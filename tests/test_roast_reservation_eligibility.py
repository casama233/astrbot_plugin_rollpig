from __future__ import annotations

import asyncio
import datetime
import importlib
import json
import logging
import sys
import threading
import types
from pathlib import Path

import pytest

from roast_reservations import create_or_join_reservation, get_reservation
from services.roast_service import RoastService
from storage import StorageManager


@pytest.mark.parametrize('pig_id', ['human', 'mc_porkchop', 'lard-pig', 'eaten', 'normal'])
def test_reserved_roast_uses_current_target_eligibility_once(tmp_path, monkeypatch, pig_id):
    if 'astrbot.api' not in sys.modules:
        api = types.ModuleType('astrbot.api')
        api.logger = logging.getLogger(__name__)
        astrbot = types.ModuleType('astrbot')
        astrbot.api = api
        monkeypatch.setitem(sys.modules, 'astrbot', astrbot)
        monkeypatch.setitem(sys.modules, 'astrbot.api', api)
    mixin = importlib.import_module('roast_reservation_feature').RoastReservationMixin
    target = object.__new__(mixin)
    storage = StorageManager(tmp_path / 'data', mode='auto').backend
    catalog = json.loads((Path(__file__).resolve().parents[1] / 'resource/pig.json').read_text())
    pig = ({'id': pig_id, 'name': pig_id} if pig_id in {'eaten', 'normal'}
           else next(p for p in catalog if p['id'] == pig_id))
    target.enable_roast_reservation = True
    target.roast_reservation_state = {}
    target._data_lock = threading.RLock()
    target._roast_reservation_lock = asyncio.Lock()
    target._today = lambda: datetime.date(2026, 11, 16)
    target._event_sender_id = lambda event: 'target'
    target._event_group_id = lambda event: 'g'
    target._get_daily_pig = lambda user, day: dict(pig)
    target._save_roast_reservations_locked = lambda: None
    target.roast_service = RoastService()
    target._roast_block_reason = target.roast_service.roast_block_reason
    target.roast_service = types.SimpleNamespace(choose_group_roast_outcome=lambda: 'success')
    events = []
    cards = []
    messages = []
    target._record_gameplay_event = lambda group, kind, **payload: events.append(kind)

    async def mention(event, user, text):
        messages.append(text)

    async def record_roast(group, user, day):
        storage.increment_roast_count(draw_date=day, group_id=group, user_id=user, cutoff_date='2026-11-01')

    async def card(event, payload, user):
        cards.append(payload['id'])

    target._send_with_mention = mention
    target._record_group_roast = record_roast
    target._send_roast_card = card
    create_or_join_reservation(target.roast_reservation_state, draw_date='2026-11-16',
                               group_id='g', target_id='target', actor_id='chef')

    class Event:
        plain_result = staticmethod(str)

        async def send(self, message):
            messages.append(message)

    async def scenario():
        event = Event()
        await target._trigger_roast_reservation_after_draw(event, {'id': 'normal'}, 'target', '今日小猪')
        first_messages = len(messages)
        await target._trigger_roast_reservation_after_draw(event, {'id': 'normal'}, 'target', '今日小猪')
        assert len(messages) == first_messages

    asyncio.run(scenario())
    row = get_reservation(target.roast_reservation_state, '2026-11-16', 'g', 'target')
    assert row['status'] == 'resolved'
    if pig_id == 'normal':
        assert row['outcome'] == 'success'
        assert cards == ['normal']
        assert events.count('roast_success') == 1
        assert storage.get_roast_count('2026-11-16', 'g', ('target',)) == 1
    else:
        assert row['outcome'] == 'blocked'
        assert cards == []
        assert 'roast_success' not in events
        assert storage.get_roast_count('2026-11-16', 'g', ('target',)) == 0
        assert target._roast_block_reason(pig, subject='target') in messages
