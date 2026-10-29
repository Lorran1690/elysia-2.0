"""Shared checks for the actual mobile frontend; no model or API fixtures."""
import hashlib
import json
import time
import uuid
from pathlib import Path

from playwright.sync_api import expect


def wait_js(page, expression, timeout=30000):
    deadline = time.monotonic() + timeout / 1000
    while not page.evaluate(expression):
        if time.monotonic() >= deadline:
            raise AssertionError('Condition timed out: ' + expression)
        page.wait_for_timeout(100)


def navigate(page, label):
    page.get_by_role('navigation', name='Navegação do telefone', exact=True).get_by_role('button', name=label, exact=True).click()


def settings(page, category):
    navigate(page, 'Configurações')
    page.get_by_label('Categoria de configurações', exact=True).select_option(category)


def assert_phone_layout(page, context):
    expect(page.locator('.desktop')).to_have_attribute('data-phone', 'true')
    measurements = page.evaluate("""()=>{
      const width=innerWidth;const selectors=['.topbar','.mobile-nav','.settings-layout','.module-page','.presence-focus','.composer','.module-form'];
      const invalid=[];for(const selector of selectors)for(const e of document.querySelectorAll(selector)){
        if(!e.getClientRects().length)continue;const r=e.getBoundingClientRect();
        if(r.left < -1 || r.right > width+1)invalid.push({selector,left:r.left,right:r.right,width});
      }
      return {viewport:width,document:document.documentElement.scrollWidth,invalid};
    }""")
    assert measurements['document'] <= measurements['viewport'] + 1, (context, measurements)
    assert not measurements['invalid'], (context, measurements)


def check_phone_navigation(page):
    navigation = page.get_by_role('navigation', name='Navegação do telefone', exact=True)
    expect(navigation).to_be_visible()
    for label in ['Conversas', 'Biblioteca', 'Criação', 'Desenvolvimento', 'Configurações']:
        button = navigation.get_by_role('button', name=label, exact=True)
        expect(button).to_be_in_viewport()
        box = button.bounding_box()
        assert box and box['height'] >= 44 and box['width'] >= 44, (label, box)
    page.get_by_role('button', name='Abrir histórico de conversas', exact=True).click()
    drawer = page.get_by_role('dialog', name='Histórico de conversas', exact=True)
    expect(drawer).to_be_visible()
    expect(drawer.get_by_role('button', name='Fechar histórico', exact=True)).to_be_in_viewport()
    drawer.get_by_role('button', name='Fechar histórico', exact=True).click()
    expect(drawer).not_to_be_visible()


def check_center(page, screenshot=None):
    page.get_by_role('button', name='Centralizar orbe ou avatar', exact=True).click()
    dialog = page.get_by_role('dialog', name='No centro do seu espaço', exact=True)
    expect(dialog).to_be_visible()
    expect(dialog.get_by_role('button', name='Fechar visualização central', exact=True)).to_be_in_viewport()
    for label in ['Orbe', 'Avatar']:
        button = dialog.get_by_role('button', name=label, exact=True)
        expect(button).to_be_in_viewport()
        button.click()
    assert page.locator('.presence-canvas canvas').count() == 1
    expect(dialog.get_by_role('button', name='Ajustar à tela', exact=True)).to_be_in_viewport()
    assert_phone_layout(page, 'center')
    if screenshot:
        page.wait_for_timeout(650)
        page.screenshot(path=str(screenshot))
    dialog.get_by_role('button', name='Fechar visualização central', exact=True).click()
    expect(dialog).not_to_be_visible()


def check_mobile_api(page):
    health = page.evaluate("fetch('/api/health').then(r=>r.json())")
    assert health['ready'] is False and health.get('platform') == 'android', health
    reply = page.evaluate("fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:[{role:'user',content:'Olá'}]})}).then(async r=>({ok:r.ok,body:await r.json()}))")
    assert not reply['ok'] and not reply['body'].get('reply'), reply
    return health


def sorted_digest(items):
    raw = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def check_vault_and_tools(page, output, native_android=False):
    title = 'Teste móvel Elysia — ação privada ' + uuid.uuid4().hex[:8]
    content = 'Registro sintético de validação. Não contém dados do proprietário.'
    navigate(page, 'Biblioteca')
    page.get_by_label('Título do registro', exact=True).fill(title)
    page.get_by_label('Conteúdo do registro', exact=True).fill(content)
    page.get_by_role('button', name='Salvar registro', exact=True).click()
    page.locator('.vault-list li').filter(has_text=title).wait_for()
    backup = page.evaluate("fetch('/api/vault/backup').then(r=>r.json())")
    assert backup['format'] == 'elysia-vault-v1'
    assert sorted_digest(backup['items']) == backup['sha256'], backup
    entry = next(i for i in backup['items'] if i['title'] == title)
    assert entry['content'] == content
    invalid = {**backup, 'sha256': '0' * 64}
    rejected = page.evaluate("async b=>{const r=await fetch('/api/vault/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});return {ok:r.ok,body:await r.json()}}", invalid)
    assert rejected['ok'] is False
    unchanged = page.evaluate("fetch('/api/vault/backup').then(r=>r.json())")
    assert unchanged == backup
    (Path(output) / 'synthetic-vault-backup.json').write_text(json.dumps(backup, ensure_ascii=False, indent=2) + '\n')
    if not native_android:
        with page.expect_download() as download:
            page.get_by_role('button', name='Exportar biblioteca', exact=True).click()
        exported = download.value
        exported.save_as(str(Path(output) / 'synthetic-vault-export.json'))
        assert json.loads((Path(output) / 'synthetic-vault-export.json').read_text()) == backup
    page.reload()
    page.get_by_role('navigation', name='Navegação do telefone', exact=True).wait_for()
    navigate(page, 'Biblioteca')
    page.locator('.vault-list li').filter(has_text=title).wait_for()
    page.get_by_label('Buscar na biblioteca', exact=True).fill(title)
    page.get_by_role('button', name='Buscar', exact=True).click()
    expect(page.locator('.vault-list li')).to_have_count(1)
    page.screenshot(path=str(Path(output) / 'library.png'))
    navigate(page, 'Desenvolvimento')
    page.get_by_role('tab', name='Utilitários', exact=True).click()
    page.get_by_label('Entrada da ferramenta', exact=True).fill('(17+3)*4')
    page.get_by_role('button', name='Executar ferramenta', exact=True).click()
    expect(page.get_by_label('Resultado da ferramenta', exact=True)).to_have_text('80')
    page.get_by_label('Ferramenta', exact=True).select_option('json_validate')
    page.get_by_label('Entrada da ferramenta', exact=True).fill('{"móvel":true}')
    page.get_by_role('button', name='Executar ferramenta', exact=True).click()
    page.get_by_label('Resultado da ferramenta', exact=True).wait_for()
    assert not page.locator('.legacy-module [role=alert]').count()
    page.get_by_role('tab', name='Editor', exact=True).click()
    page.get_by_label('Linguagem do código', exact=True).select_option('json')
    page.get_by_label('Editor de código', exact=True).fill('{"elysia":"android"}')
    page.get_by_role('button', name='Validar sintaxe', exact=True).click()
    page.locator('.module-notice').wait_for()
    assert not page.locator('.legacy-module [role=alert]').count()
    return {'indexeddb_vault_persistence': True, 'vault_backup_python_sha256_compatible': True, 'invalid_restore_preserves_data': True, 'calculator_and_json_tools': True, 'code_editor_and_json_validation': True}


def check_music_and_png(page, output, native_android=False):
    settings(page, 'audio')
    page.get_by_role('button', name='Reproduzir música', exact=True).click()
    wait_js(page, "document.querySelector('audio[data-owner=elysia-background]')?.currentTime > .2", timeout=25000)
    page.get_by_label('Volume da música', exact=True).evaluate("e=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,'27');e.dispatchEvent(new Event('input',{bubbles:true}));}")
    wait_js(page, "document.querySelector('audio[data-owner=elysia-background]').volume===.27")
    page.get_by_role('button', name='Pausar música', exact=True).click()
    wait_js(page, "document.querySelector('audio[data-owner=elysia-background]').paused")
    navigate(page, 'Criação')
    page.get_by_role('tab', name='Composição e áudio', exact=True).click()
    page.get_by_role('button', name='Gerar PNG', exact=True).click()
    page.get_by_role('button', name='Baixar arquivo gerado', exact=True).wait_for()
    assert page.locator('.studio-output img').evaluate('e=>e.complete&&e.naturalWidth>0')
    page.screenshot(path=str(Path(output) / 'composition.png'))
    if not native_android:
        with page.expect_download() as download:
            page.get_by_role('button', name='Baixar arquivo gerado', exact=True).click()
        download.value.save_as(str(Path(output) / 'synthetic-composition.png'))
        assert (Path(output) / 'synthetic-composition.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    return {'actual_audio_play_pause_volume': True, 'png_composition_generated': True, 'png_browser_download': not native_android}


def capture_failure(page, output, failure):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'failure.json').write_text(json.dumps({'exception': str(failure)}, ensure_ascii=False, indent=2) + '\n')
    if page and not page.is_closed():
        try:
            page.screenshot(path=str(output / 'failure.png'), timeout=5000)
            (output / 'failure-visible.txt').write_text(page.locator('body').inner_text(timeout=3000)[:100000])
        except Exception:
            pass
