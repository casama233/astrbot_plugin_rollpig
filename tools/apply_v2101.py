from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {count}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


# Version metadata.
replace_once('metadata.yaml', 'version: "2.10.0"', 'version: "2.10.1"')
replace_once(
    'main.py',
    'AstrBot-RollPig/2.10.0 (+https://github.com/casama233/astrbot_plugin_rollpig)',
    'AstrBot-RollPig/2.10.1 (+https://github.com/casama233/astrbot_plugin_rollpig)',
)
updater = read('updater.py')
if '2.10.0' in updater:
    write('updater.py', updater.replace('2.10.0', '2.10.1'))

# Make migration requests observable in AstrBot logs, including safe failures.
replace_once(
    'main.py',
    '            async with self._storage_admin_lock:\n'
    '                data = await asyncio.to_thread(self.storage_manager.migrate_to_sqlite)\n',
    '            logger.info("开始 SQLite 存储迁移：准备备份 JSON、建立临时数据库并执行对账")\n'
    '            async with self._storage_admin_lock:\n'
    '                data = await asyncio.to_thread(self.storage_manager.migrate_to_sqlite)\n',
)
replace_once(
    'main.py',
    '            return self._jsonify({"status": "ok", "data": data})\n'
    '        except StorageMigrationError as exc:\n'
    '            return self._jsonify({"status": "error", "message": str(exc)})\n'
    '        except Exception as exc:\n'
    '            logger.exception("SQLite 迁移失败")\n',
    '            return self._jsonify({"status": "ok", "data": data})\n'
    '        except StorageMigrationError as exc:\n'
    '            logger.warning(f"SQLite 存储迁移未切换后端：{exc}")\n'
    '            return self._jsonify({"status": "error", "message": str(exc)})\n'
    '        except Exception as exc:\n'
    '            logger.exception("SQLite 迁移失败")\n',
)

# Plugin pages run inside a sandbox that may block native window.confirm().
# Intercept the affected clicks, show an in-page modal, then invoke the existing
# handler while temporarily satisfying its legacy synchronous confirmation.
feedback_path = 'pages/pig-manager/ui-feedback.js'
feedback = read(feedback_path)
if 'function showPageConfirm' in feedback:
    raise RuntimeError('confirmation layer already installed')
marker = '\n})();\n'
if not feedback.endswith(marker):
    raise RuntimeError('ui-feedback.js closing marker not found')
confirmation_layer = r'''

  function ensurePageConfirmDialog() {
    let overlay = $('pageConfirmDialog');
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'pageConfirmDialog';
    overlay.setAttribute('role', 'presentation');
    overlay.style.cssText = 'display:none;position:fixed;inset:0;z-index:10050;background:rgba(7,10,18,.68);backdrop-filter:blur(8px);align-items:center;justify-content:center;padding:24px';
    overlay.innerHTML = `
      <section role="dialog" aria-modal="true" aria-labelledby="pageConfirmTitle" style="width:min(460px,100%);border:1px solid rgba(255,255,255,.18);border-radius:22px;background:var(--panel,#171a24);box-shadow:0 28px 80px rgba(0,0,0,.48);padding:24px">
        <div class="eyebrow">Confirm Action</div>
        <h2 id="pageConfirmTitle" style="margin:8px 0 10px">确认操作</h2>
        <p id="pageConfirmMessage" class="panel-desc" style="white-space:pre-wrap;line-height:1.7;margin-bottom:22px"></p>
        <div class="dialog-actions">
          <button class="btn ghost" type="button" id="pageConfirmCancel">取消</button>
          <button class="btn" type="button" id="pageConfirmAccept">继续</button>
        </div>
      </section>`;
    document.body.appendChild(overlay);
    return overlay;
  }

  function showPageConfirm({title, message, confirmText = '继续', dangerous = false}) {
    const overlay = ensurePageConfirmDialog();
    const titleNode = $('pageConfirmTitle');
    const messageNode = $('pageConfirmMessage');
    const cancel = $('pageConfirmCancel');
    const accept = $('pageConfirmAccept');
    titleNode.textContent = title;
    messageNode.textContent = message;
    accept.textContent = confirmText;
    accept.classList.toggle('danger', dangerous);
    overlay.style.display = 'flex';
    return new Promise(resolve => {
      let settled = false;
      const finish = value => {
        if (settled) return;
        settled = true;
        overlay.style.display = 'none';
        overlay.removeEventListener('click', onOverlay);
        document.removeEventListener('keydown', onKey, true);
        resolve(value);
      };
      const onOverlay = event => { if (event.target === overlay) finish(false); };
      const onKey = event => {
        if (event.key === 'Escape') {
          event.preventDefault();
          finish(false);
        }
      };
      cancel.onclick = () => finish(false);
      accept.onclick = () => finish(true);
      overlay.addEventListener('click', onOverlay);
      document.addEventListener('keydown', onKey, true);
      requestAnimationFrame(() => accept.focus());
    });
  }

  const sandboxConfirmActions = {
    storageMigrateBtn: {
      title: '迁移到 SQLite',
      message: '系统会先完整备份关键 JSON，再建立临时数据库、导入、哈希对账并执行完整性检查。任何一步失败都会继续使用原 JSON。',
      confirmText: '开始迁移',
      bypassCount: 1
    },
    storageRebuildBtn: {
      title: '重建 SQLite 索引',
      message: '将从 SQLite 内的兼容文档事务性重建查询索引。不会改变现有抽取结果，但重建期间会暂时锁定数据库写入。',
      confirmText: '开始重建',
      bypassCount: 1
    },
    storageRollbackBtn: {
      title: '回滚到 JSON',
      message: 'SQLite 中的最新数据将先原子写回 JSON 并完成哈希对账，原数据库会改名保留而不会删除。回滚后当前实例会立即改用 JSON。',
      confirmText: '确认回滚',
      dangerous: true,
      bypassCount: 2
    },
    updateApplyBtn: {
      title: '安装稳定版更新',
      message: '更新器会下载官方稳定 Release，执行来源、校验和、压缩包、metadata 与 Python 语法检查，并在替换代码前完整备份。安装后必须重启 AstrBot。',
      confirmText: '安装更新',
      bypassCount: 1
    },
    aiDraftBtn: {
      title: '覆盖现有 AI 文案',
      message: '当前描述或完整文案已有内容。继续后，AI 生成结果会覆盖这些字段，但在保存小猪前仍可手动修改。',
      confirmText: '覆盖并生成',
      bypassCount: 1,
      when: () => Boolean(
        ($('pigDescription')?.value || '').trim() ||
        ($('pigAnalysis')?.value || '').trim()
      )
    }
  };

  function invokeLegacyConfirmedHandler(button, bypassCount) {
    const handler = button?.onclick;
    if (typeof handler !== 'function') throw new Error('操作处理器尚未载入，请刷新页面后重试。');
    const previousConfirm = window.confirm;
    let remaining = Math.max(0, Number(bypassCount) || 0);
    window.confirm = () => {
      if (remaining <= 0) return false;
      remaining -= 1;
      return true;
    };
    try {
      const result = handler.call(button, new MouseEvent('click', {cancelable: true}));
      if (result && typeof result.catch === 'function') {
        result.catch(error => console.error('[rollpig] confirmed action failed', error));
      }
    } finally {
      window.confirm = previousConfirm;
    }
  }

  let pageConfirmBusy = false;
  document.addEventListener('click', async event => {
    const button = event.target.closest('button');
    const config = button && sandboxConfirmActions[button.id];
    if (!config || button.disabled || (config.when && !config.when())) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (pageConfirmBusy) return;
    pageConfirmBusy = true;
    try {
      const accepted = await showPageConfirm(config);
      if (accepted) invokeLegacyConfirmedHandler(button, config.bypassCount);
    } catch (error) {
      const message = errorText(error);
      setFeedback(config.feedback || 'storageFeedback', `无法启动操作：${message}`);
      console.error('[rollpig] page confirmation failed', error);
    } finally {
      pageConfirmBusy = false;
    }
  }, true);
'''
write(feedback_path, feedback[:-len(marker)] + confirmation_layer + marker)

# Regression coverage.
test_path = 'tests/test_dashboard_feedback.py'
tests = read(test_path)
addition = '''\n\ndef test_feedback_layer_uses_in_page_confirmation_for_sandboxed_plugin_pages():\n    assert "function showPageConfirm" in FEEDBACK\n    assert "pageConfirmDialog" in FEEDBACK\n    for button_id in (\n        "storageMigrateBtn",\n        "storageRebuildBtn",\n        "storageRollbackBtn",\n        "updateApplyBtn",\n        "aiDraftBtn",\n    ):\n        assert button_id in FEEDBACK\n    assert "invokeLegacyConfirmedHandler" in FEEDBACK\n    assert "window.confirm = () =>" in FEEDBACK\n\n\ndef test_sqlite_migration_is_logged_before_work_and_on_safe_failure():\n    assert "开始 SQLite 存储迁移" in MAIN\n    assert "SQLite 存储迁移未切换后端" in MAIN\n'''
if 'test_feedback_layer_uses_in_page_confirmation_for_sandboxed_plugin_pages' in tests:
    raise RuntimeError('dashboard confirmation tests already installed')
write(test_path, tests.rstrip() + addition + '\n')

# Release notes.
changelog = read('CHANGELOG.md')
entry = '''# 更新\n## v2.10.1 (2026-08-04)\n### 管理面板确认框与迁移反馈热修复\n- 修复 AstrBot Plugin Page 的 iframe sandbox 阻止原生 `window.confirm()`，导致“迁移 SQLite”等按钮点击后无请求、无日志、无前端反馈的问题。\n- 迁移、重建索引、回滚 JSON、安装更新和 AI 覆盖文案改用页面内确认对话框；继续沿用原有 CSRF、互斥锁和操作耗时反馈。\n- SQLite 迁移在开始执行及安全失败时写入明确日志，方便区分“前端未发请求”和“后端迁移失败”。\n\n'''
if not changelog.startswith('# 更新\n'):
    raise RuntimeError('CHANGELOG header not found')
write('CHANGELOG.md', entry + changelog[len('# 更新\n'):])

print('v2.10.1 hotfix applied')
