import asyncio
import nodriver as uc

url = 'https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cib'

import asyncio
import nodriver as uc

async def main():
    browser = await uc.start(headless=False)
    try:
        page = await browser.get(url)
        # Aguarda o carregamento inicial
        await page.wait(3)
        # Localiza o campo
        element = await page.select('input[name="niContribuinte"]')
        if element is None:
            raise RuntimeError("Campo niContribuinte não encontrado.")
        # Foca e preenche o campo
        await element.click()
        await element.send_keys("77149610")
        await page.wait(1)
        # Localiza o botão
        button = await page.select("button.br-button.primary.btn-acao")
        if button is None:
            raise RuntimeError("Botão não encontrado.")
        # Clica no botão
        await button.click()
        # Aguarda o resultado
        await page.wait(10)
    finally:
        await browser.stop()


asyncio.run(main())