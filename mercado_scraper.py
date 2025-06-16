import pandas as pd
import re
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuração do WebDriver ---

from driver_config import setup_driver


# --- Funções de Limpeza e Extração de Dados Específicos ---
def clean_price(price_str_original):
    """
    Limpa e converte uma string de preço para um valor float.
    Lida com formatos como "R$ 153,10", "153 reais e 10 centavos", etc.
    """
    if not price_str_original: return None
    s = str(price_str_original).lower().strip()
    # print(f"  clean_price input: '{s}'") # Para depuração

    # Remove pontos de milhar ANTES de tentar o regex para "reais e centavos"
    # Isso ajuda se o número em si tiver pontos, ex: "1.234,50 reais" -> "1234,50 reais"
    s_no_thousands = re.sub(r'\.(?=\d{3}(?:,|\sreais|$))', '', s) 
    # print(f"  s_no_thousands: '{s_no_thousands}'") # DEBUG
    
    # Regex para "X reais [e|,|com] Y centavos" ou "X reais"
    # Captura os números de reais e, opcionalmente, os de centavos.
    # O grupo dos reais ([\d,]+) permite vírgulas, que são removidas depois.
    # O grupo dos centavos ([\d,]+) também permite vírgulas (embora incomum para centavos).
    match_reais_centavos = re.search(r'([\d,]+)\s*reais(?:\s*(?:e|,|com)\s*([\d,]+)\s*centavos)?', s_no_thousands)
    if match_reais_centavos:
        reais_part_str = match_reais_centavos.group(1).replace(',', '') # Ex: "153"
        centavos_part_str = match_reais_centavos.group(2) # Ex: "10" ou None
        
        # print(f"  Reais part str: '{reais_part_str}', Centavos part str: '{centavos_part_str}'") # DEBUG
        try:
            reais_val = int(reais_part_str)
            if centavos_part_str:
                centavos_val = int(centavos_part_str.replace(',', ''))
                # print(f"  Reais val: {reais_val}, Centavos val: {centavos_val}") # DEBUG
                final_float = float(f"{reais_val}.{centavos_val:02d}") # Garante formato como 153.10
                # print(f"  Returning from reais_centavos: {final_float}") # DEBUG
                return final_float
            else: # Apenas reais, sem centavos explicitados na forma "X centavos"
                # print(f"  Reais val: {reais_val}, No centavos part.") # DEBUG
                final_float = float(reais_val)
                # print(f"  Returning from reais_only: {final_float}") # DEBUG
                return final_float
        except ValueError as e_val:
            # print(f"  ValueError in reais_centavos block: {e_val}") # DEBUG
            pass # Se falhar, continua para a lógica de fallback

    # Lógica de fallback (se o regex acima não casar ou falhar na conversão)
    # Remove "reais" do final, se houver
    s = re.sub(r'\s*reais?$', '', s).strip()
    # Remove "R$" do início
    if s.startswith("r$"): s = s[2:].strip()
    # Remove pontos de milhar (ex: "1.234,56" -> "1234,56")
    s = re.sub(r'\.(?=\d{3}(?:,|$))', '', s) 
    # Troca vírgula decimal por ponto (ex: "1234,56" -> "1234.56")
    s = s.replace(',', '.') 
    # Remove quaisquer caracteres não numéricos restantes, exceto o ponto decimal
    s = re.sub(r'[^\d\.]', '', s) 
    # print(f"  Fallback processed s: '{s}'") # DEBUG
    try:
        val = float(s)
        # print(f"  Returning from fallback: {val}") # DEBUG
        return val
    except ValueError:
        # print(f"Não foi possível converter o preço '{price_str_original}' (processado como '{s}') para float na lógica de fallback.")
        return price_str_original # Retorna o original se todas as tentativas falharem

def extract_review_count(count_text):
    """Extrai o número de avaliações de uma string (ex: "(106 opiniões)" -> 106)."""
    if not count_text: return None
    match = re.search(r'(\d+)', count_text) 
    return int(match.group(1)) if match else None

# --- Função Principal de Scraping da Página do Produto ---
def scrape_mercado_livre_product(url, driver):
    """Coleta dados de uma página de produto específica do Mercado Livre."""
    driver.get(url)
    # Pausa aleatória para simular comportamento humano e permitir carregamento
    time.sleep(random.uniform(3.5, 5.5)) 
    wait = WebDriverWait(driver, 20) # Tempo máximo de espera para elementos

    data = {'link_anuncio': url} # Inicializa dicionário de dados com o link

    # --- Extração do Título ---
    try:
        title_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'h1.ui-pdp-title')))
        data['titulo'] = title_element.text.strip()
    except Exception: data['titulo'] = None # Define como None se não encontrar

    # --- Extração do Preço ---
    data['preco'] = None # Inicializa como None
    try:
        # Lista de seletores CSS para encontrar o container do preço
        price_container_selectors = [
            "div.ui-pdp-price__main-container span.andes-money-amount",
            "div.ui-pdp-price__co-container span.andes-money-amount" # Fallback
        ]
        price_container = None
        for selector in price_container_selectors: # Tenta cada seletor
            try:
                price_container = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                if price_container: break # Usa o primeiro que encontrar
            except: continue
        
        if not price_container: 
            # Última tentativa com XPath mais genérico se CSS falhar
            try:
                price_container = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'ui-pdp-price__')]//span[contains(@class,'andes-money-amount__fraction')]/parent::span")))
            except:
                 print("Container de preço não encontrado.")
                 raise Exception("Container de preço não encontrado") # Força erro se realmente não achar

        # Prioriza o 'aria-label', que geralmente tem o preço de forma mais completa
        raw_price_from_aria = price_container.get_attribute('aria-label')
        parsed_price_from_aria = None

        if raw_price_from_aria:
            # print(f"Debug Preço: aria-label encontrado: '{raw_price_from_aria}'") # Para depuração
            parsed_price_from_aria = clean_price(raw_price_from_aria)
            # Considera sucesso apenas se clean_price retornar um float
            if not isinstance(parsed_price_from_aria, float):
                # print(f"Debug Preço: clean_price do aria-label não retornou float: '{parsed_price_from_aria}'") # Para depuração
                parsed_price_from_aria = None 
        
        if parsed_price_from_aria is not None:
            data['preco'] = parsed_price_from_aria
            # print(f"Preço obtido via aria-label: {raw_price_from_aria} -> {data['preco']}") # Para depuração
        else: 
            # print("Preço via aria-label não foi ideal ou falhou, tentando fração/centavos.") # Para depuração
            # Se aria-label falhou ou não foi útil, tenta construir a partir das tags de fração e centavos
            fraction_elements = driver.find_elements(By.CSS_SELECTOR, 'div.ui-pdp-price__main-container span.andes-money-amount__fraction, div.ui-pdp-price__co-container span.andes-money-amount__fraction, span.price-tag-fraction')
            fraction = fraction_elements[0].text.strip() if fraction_elements and fraction_elements[0].text.strip() else ""
            
            cents_elements = driver.find_elements(By.CSS_SELECTOR, 'div.ui-pdp-price__main-container span.andes-money-amount__cents, div.ui-pdp-price__co-container span.andes-money-amount__cents, span.price-tag-cents')
            cents = cents_elements[0].text.strip() if cents_elements and cents_elements[0].text.strip() else ""
            
            raw_price_from_frac_cents = ""
            if fraction and cents: # Se ambos existem, monta como "XXX,YY"
                raw_price_from_frac_cents = f"{fraction},{cents}"
            elif fraction: # Se só fração existe
                raw_price_from_frac_cents = fraction 
            elif price_container.text: # Fallback para o texto geral do container
                 raw_price_from_frac_cents = price_container.text.strip()

            if raw_price_from_frac_cents:
                data['preco'] = clean_price(raw_price_from_frac_cents)
                # print(f"Preço obtido via fração/centavos: {raw_price_from_frac_cents} -> {data['preco']}") # Para depuração
            # Último recurso: se o aria-label existia mas foi descartado, e frac/cents também falhou
            elif raw_price_from_aria and data['preco'] is None: 
                data['preco'] = clean_price(raw_price_from_aria) 
                # print(f"Preço obtido via aria-label (tentativa final): {raw_price_from_aria} -> {data['preco']}") # Para depuração
                
    except Exception as e:
        print(f"Erro Preço: {type(e).__name__} - {e}")


    # --- Extração do Nome do Vendedor ---
    data['vendedor'] = None
    try:
        # Lista de XPaths priorizados para encontrar o nome do vendedor
        seller_xpaths_priority = [
            # XPaths específicos fornecidos pelo usuário (maior prioridade)
            {"xpath": "//button[contains(@class, 'ui-pdp-seller__link-trigger-button')]/span[not(contains(@class, 'ui-pdp-seller__label-sold')) and normalize-space(text())]", "type": "text"},
            {"xpath": "//span[contains(@class, 'ui-pdp-seller__label-sold')]/following-sibling::span[1][normalize-space(text())]", "type": "text"},
            # Outros XPaths testados anteriormente
            {"xpath": "//a[starts-with(@aria-label, 'Informações sobre o vendedor')]/span[contains(@class, 'ui-pdp-action-modal__link')]", "type": "aria_or_text"},
            {"xpath": "//div[contains(@class,'ui-pdp-seller__header--official-store-label')]//span[@class='ui-pdp-action-modal__link']", "type": "text"},
            {"xpath": "//p[contains(translate(lower-case(text()), 'áéíóúàèìòùäëïöüñç', 'aeiouaeiouaeiounc'), 'vendido por')]/a/span[contains(@class,'ui-pdp-action-modal__link') or contains(@class,'ui-pdp-color--BLUE')]", "type": "text"},
            {"xpath": "//div[contains(@class, 'ui-pdp-seller__info-container')]//h3[contains(@class, 'ui-pdp-seller__nickname')]", "type": "text"},
            {"xpath": "//a[contains(@class, 'ui-pdp-seller__action-link') and contains(@href, 'perfil.mercadolivre.com.br')]", "type": "text"},
        ]

        for item in seller_xpaths_priority:
            elements = driver.find_elements(By.XPATH, item["xpath"])
            if elements:
                element_to_check = elements[0]
                vendedor_text = ""
                if item["type"] == "aria_or_text": # Tenta pegar texto e, se falhar, extrai do aria-label
                    vendedor_text = element_to_check.text.strip()
                    if not vendedor_text and element_to_check.get_attribute('aria-label'):
                        aria_label = element_to_check.get_attribute('aria-label')
                        # Extrai o nome após "Informações sobre o vendedor "
                        match_aria = re.search(r'Informações sobre o vendedor\s*(.+)', aria_label, re.IGNORECASE)
                        if match_aria: vendedor_text = match_aria.group(1).strip()
                elif item["type"] == "text": # Pega o texto diretamente
                    vendedor_text = element_to_check.text.strip()
                
                if vendedor_text and len(vendedor_text) > 1: # Garante que não é um texto muito curto/inválido
                    data['vendedor'] = vendedor_text
                    # print(f"Vendedor encontrado com XPath '{item['xpath']}': {data['vendedor']}") # Para depuração
                    break # Para de tentar outros XPaths se encontrou
        # if not data['vendedor']: print("Vendedor não encontrado.") # Para depuração
            
    except Exception as e: 
        print(f"Erro Vendedor: {type(e).__name__} - {e}")


    # --- Extração de Avaliações ---
    data['avaliacao_nota'] = None; data['avaliacao_numero'] = None
    try:
        # Tenta rolar para a seção de avaliações para ajudar no carregamento dinâmico
        review_section_estimate = driver.find_elements(By.XPATH, "//*[contains(@class, 'review') or contains(@class, 'opinioes_search_result_V2') or contains(@class, 'andes-review-summary')]")
        if review_section_estimate:
            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", review_section_estimate[0])
                # Espera que um container de reviews seja visível
                WebDriverWait(driver, 5).until(EC.visibility_of_any_elements_located((By.XPATH, "//div[contains(@class, 'andes-review-summary__root')] | //div[contains(@class, 'ui-pdp-reviews__summary')]")))
            except Exception: pass # Continua mesmo se o scroll/wait falhar

        # Tenta a estrutura mais nova (Andes UI)
        andes_review_root_xpath = "//div[contains(@class, 'andes-review-summary__root')]"
        review_roots = driver.find_elements(By.XPATH, andes_review_root_xpath)
        if review_roots:
            try:
                rating_el = review_roots[0].find_element(By.XPATH, ".//span[contains(@class, 'andes-review-summary__rating')]")
                if rating_el.text.strip() and re.match(r"[\d\.,]+", rating_el.text.strip()): data['avaliacao_nota'] = rating_el.text.strip()
            except Exception: pass # Silencia erro se elemento específico não for encontrado
            try:
                count_el = review_roots[0].find_element(By.XPATH, ".//span[contains(@class, 'andes-review-summary__reviews-count')]")
                data['avaliacao_numero'] = extract_review_count(count_el.text.strip())
            except Exception: pass
        
        # Fallback para estruturas mais antigas se a nova não fornecer dados
        if data['avaliacao_nota'] is None or data['avaliacao_numero'] is None:
            rating_fallback_elements = driver.find_elements(By.XPATH, "//p[contains(@class, 'ui-review-capability__rating__average')] | //span[contains(@class, 'ui-pdp-review__rating')]")
            if data['avaliacao_nota'] is None and rating_fallback_elements:
                for el in rating_fallback_elements:
                    if el.text.strip() and re.match(r"[\d\.,]+", el.text.strip()): data['avaliacao_nota'] = el.text.strip(); break
            
            count_fallback_elements = driver.find_elements(By.XPATH, "//p[contains(@class, 'ui-review-capability__rating__total-reviews')] | //span[contains(@class, 'ui-pdp-review__amount')]")
            if data['avaliacao_numero'] is None and count_fallback_elements:
                 for el in count_fallback_elements:
                    extracted_count = extract_review_count(el.text.strip())
                    if extracted_count is not None: data['avaliacao_numero'] = extracted_count; break
    except Exception as e: print(f"Erro Avaliações: {type(e).__name__}")

    # --- Extração da Descrição (com tentativa de expandir) ---
    data['descricao'] = None
    try:
        # Tenta fechar overlays/cookies ANTES de interagir com "Ver descrição"
        cookie_banner_interceptor_xpath = "//p[@data-testid='text:main-text' and contains(@class, 'cookie-consent-banner-opt-out__message')]"
        cookie_close_xpaths = [
            "//button[@data-testid='cookie-banner-close-button']",
            "//div[contains(@class,'cookie-consent-banner-actions')]//button[contains(@class,'andes-button--loud')]",
            "//button[contains(translate(normalize-space(text()), 'ACEPTRÁÉÍÓÚ', 'aceptráéíóú'), 'aceitar') and (contains(@class, 'cookie') or contains(@class, 'consent'))]",
            "//button[contains(translate(normalize-space(text()), 'ENTDIÁÉÍÓÚ', 'entdiáéíóú'), 'entendi') and (contains(@class, 'cookie') or contains(@class, 'consent'))]",
            "//div[contains(@class, 'cookie-consent')]//button[contains(translate(normalize-space(text()), 'FECHRÁÉÍÓÚ', 'fechráéíóú'), 'fechar') or contains(@aria-label, 'Fechar') or contains(@class, 'close')]",
        ]
        banner_closed_this_time = False
        for ck_xpath_idx, ck_xpath in enumerate(cookie_close_xpaths):
            try:
                cookie_buttons = driver.find_elements(By.XPATH, ck_xpath)
                if cookie_buttons and cookie_buttons[0].is_displayed() and cookie_buttons[0].is_enabled():
                    # print(f"Tentando fechar overlay/cookie com XPath {ck_xpath_idx+1}...") # Debug
                    driver.execute_script("arguments[0].click();", cookie_buttons[0])
                    time.sleep(random.uniform(1.0, 1.5)) 
                    # print("Possível overlay/cookie fechado.") # Debug
                    try: 
                        WebDriverWait(driver, 2).until_not(EC.visibility_of_element_located((By.XPATH, cookie_banner_interceptor_xpath)))
                        # print("Banner de cookie que interceptava não está mais visível.") # Debug
                        banner_closed_this_time = True; break 
                    except: pass 
            except Exception: continue
        # if not banner_closed_this_time: print("Não foi possível confirmar o fechamento do banner de cookie interceptador ou ele não estava presente.") # Debug
        
        desc_container_xpath = "//div[contains(@class, 'ui-pdp-description__content')] | //div[contains(@class, 'ui-pdp-description') and not(contains(@class,'ui-pdp-description__title'))][normalize-space()]"
        
        # XPath para o link "Ver descrição completa" baseado no HTML fornecido pelo usuário
        see_more_xpath_specific = "//a[@data-testid='action-collapsable-target' and contains(@class, 'ui-pdp-collapsable__action') and (contains(translate(normalize-space(@title), 'VERDESCÃOCOMPLTÁÉÍÓÚ', 'verdescãocompltáéíóú'), 'ver descrição completa') or contains(translate(normalize-space(text()), 'VERDESCÃOCOMPLTÁÉÍÓÚ', 'verdescãocompltáéíóú'), 'ver descrição completa'))]"
        
        see_more_elements = []
        try: 
            # Espera que o elemento esteja presente e potencialmente clicável
            see_more_elements = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, see_more_xpath_specific))
            )
        except Exception: 
            # print("Botão/link 'Ver descrição completa' (específico) não encontrado inicialmente ou não pronto.") # Debug
            pass 

        if see_more_elements and see_more_elements[0].is_displayed() and see_more_elements[0].is_enabled():
            # print("Botão/link 'Ver descrição completa' encontrado. Tentando clicar...") # Debug
            clicked_successfully = False
            try:
                # Espera o elemento ser clicável antes de tentar a interação
                button_to_click = wait.until(EC.element_to_be_clickable((By.XPATH, see_more_xpath_specific)))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", button_to_click)
                time.sleep(0.7) # Pausa após scroll
                # Tenta clicar com JavaScript primeiro, pois pode ser mais robusto contra interceptações
                driver.execute_script("arguments[0].click();", button_to_click)
                # print("'Ver descrição completa' clicado via JavaScript.") # Debug
                time.sleep(random.uniform(1.5, 2.5)) # Espera para o conteúdo carregar/expandir
                clicked_successfully = True
            except Exception as e_js_click: 
                print(f"Erro ao clicar em 'Ver descrição completa' (JS): {e_js_click}. Tentando clique Selenium.")
                try: 
                    # Fallback para clique normal do Selenium se o JS falhar
                    button_to_click = wait.until(EC.element_to_be_clickable((By.XPATH, see_more_xpath_specific))) # Re-localiza para garantir estado
                    button_to_click.click()
                    # print("'Ver descrição completa' clicado via Selenium.") # Debug
                    time.sleep(random.uniform(1.5, 2.5))
                    clicked_successfully = True
                except Exception as e_selenium_click:
                     print(f"Erro ao clicar em 'Ver descrição completa' (Selenium): {e_selenium_click}")
            
            # if not clicked_successfully: print("Falha ao clicar no botão 'Ver descrição completa'.") # Debug
        # else:  # Debug
            # print("Botão/link 'Ver descrição completa' (específico) não encontrado ou não interagível.")
            
        # Após a tentativa de clique (ou se não havia botão), coleta a descrição
        # É importante re-localizar o container da descrição pois seu conteúdo pode ter mudado
        desc_container_elements = driver.find_elements(By.XPATH, desc_container_xpath)
        if desc_container_elements:
            descricao_bruta = desc_container_elements[0].get_attribute('innerText').strip()
            # Remove quebras de linha e substitui por um espaço, depois remove espaços múltiplos
            data['descricao'] = re.sub(r'\s+', ' ', descricao_bruta.replace('\n', ' ').replace('\r', ' ')).strip()
        else:
            # print("Container da descrição não encontrado.") # Debug
            data['descricao'] = None

    except Exception as e_desc: 
        print(f"Erro Descrição: {type(e_desc).__name__} - {e_desc}")
        data['descricao'] = None
        
    # 'dados_extras' não é mais coletado
    data['dados_extras'] = None 
    return data

def search_mercado_livre_and_get_links(search_term, driver, max_links=10):
    search_term_path = search_term.replace(" ", "-")
    search_term_query = search_term.replace(" ", "+")
    search_url = f"https://lista.mercadolivre.com.br/{search_term_path}#D[A:{search_term_query},L:GALERY]"

    print(f"Navegando para a página de busca: {search_url}")
    driver.get(search_url)
    time.sleep(random.uniform(2, 4))

    try:
        WebDriverWait(driver, 7).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Entendi') or contains(@data-testid, 'action:understood-button') or @data-testid='cookie-banner-close-button'] | //button[contains(@class, 'cookie-consent-banner__cta')]"))).click()
        # print("Popup de cookie fechado.") # Debug
        time.sleep(random.uniform(1, 2))
    except Exception: 
        # print("Nenhum popup de cookie manipulado.") # Debug
        pass


    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//ol[contains(@class, 'ui-search-layout')] | //section[contains(@class, 'ui-search-results')]")))
        # print("Container de resultados de busca principal encontrado.") # Debug
    except Exception as e: print(f"Container de resultados de busca não encontrado: {e}. Nenhum link será coletado."); return []

    product_links = []; seen_links = set()
    for i in range(2): # Faz alguns scrolls para carregar mais itens
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)*0.4});")
        time.sleep(random.uniform(2, 4)) 

    product_link_xpaths = [
        "//li[contains(@class, 'ui-search-layout__item')]//a[contains(@class, 'ui-search-link') and @href]",
        "//li[contains(@class, 'ui-search-layout__item')]//div[contains(@class, 'andes-card')]//a[@href and (contains(@href, '/MLB-') or contains(@href, '/p/MLB'))]",
        "//li[contains(@class, 'ui-search-layout__item')]//div[contains(@class, 'ui-search-result__image')]//a[@href and (contains(@href, '/MLB-') or contains(@href, '/p/MLB'))]",
        "//li[contains(@class, 'ui-search-layout__item')]//h2/a[@href and (contains(@href, '/MLB-') or contains(@href, '/p/MLB'))]",
    ]
    link_elements_candidates = []
    for xpath_option in product_link_xpaths:
        elements = driver.find_elements(By.XPATH, xpath_option)
        if elements: link_elements_candidates.extend(elements)
    
    unique_link_elements = []
    temp_hrefs_for_uniqueness = set()
    for el in link_elements_candidates:
        try:
            href_val = el.get_attribute('href')
            if href_val and href_val not in temp_hrefs_for_uniqueness:
                unique_link_elements.append(el)
                temp_hrefs_for_uniqueness.add(href_val)
        except Exception: continue # Elemento pode ter se tornado obsoleto
    link_elements = unique_link_elements

    # print(f"Encontrados {len(link_elements)} elementos de link candidatos.") # Debug
    for link_el in link_elements:
        try:
            href = link_el.get_attribute('href')
            # Filtros para garantir que é um link de produto válido
            if href and \
               ("mercadolivre.com.br/" in href) and \
               ("/MLB-" in href or "/p/MLB" in href) and \
               "click?" not in href and \
               "/promocoes" not in href and \
               "/ofertas" not in href and \
               "/gz/checkout" not in href and \
               "/ayuda_home" not in href : # Evita links de ajuda, etc.

                clean_href = href.split('#')[0] # Remove fragmentos
                # Para links de anúncio (/MLB-), remove parâmetros de query
                if "/MLB-" in clean_href and "?" in clean_href: 
                    clean_href = clean_href.split('?')[0] 
                
                if clean_href not in seen_links:
                    product_links.append(clean_href)
                    seen_links.add(clean_href)
                    if len(product_links) >= max_links: break
        except Exception: continue
    # print(f"Coletados {len(product_links)} links de produtos únicos.") # Debug
    return product_links[:max_links]

def save_to_csv(data_list, filename="mercado_livre_produtos.csv"):
    if not data_list: 
        print("Nenhum dado para salvar.")
        return
    
    processed_data_for_df = []
    for item_original in data_list:
        item = item_original.copy() 
        flat_item = {}
        flat_item['link_anuncio'] = item.get('link_anuncio')
        flat_item['titulo'] = item.get('titulo')
        
        price_float = item.get('preco')
        if isinstance(price_float, (float, int)):
            try:
                # Formata para "R$ XXX,YY"
                price_str_simple = f"{price_float:.2f}".replace('.', ',')
                flat_item['preco'] = f"R$ {price_str_simple}"
            except (TypeError, ValueError): 
                flat_item['preco'] = price_float # Mantém o float se a formatação falhar
        elif price_float is not None: # Se já for string (ex: erro de clean_price)
             flat_item['preco'] = price_float
        else:
            flat_item['preco'] = None # Se for None
            
        flat_item['vendedor'] = item.get('vendedor')
        flat_item['avaliacao_nota'] = item.get('avaliacao_nota')
        flat_item['avaliacao_numero'] = item.get('avaliacao_numero')
        flat_item['descricao'] = item.get('descricao')
        
        processed_data_for_df.append(flat_item)

    df = pd.DataFrame(processed_data_for_df)
    
    # Colunas definidas, sem 'dados_extras'
    final_columns_order = ['link_anuncio', 'titulo', 'preco', 'vendedor', 
                           'avaliacao_nota', 'avaliacao_numero', 'descricao']
    
    # Garante que todas as colunas desejadas existam no DataFrame, preenchendo com None/NaN se faltar
    for col in final_columns_order:
        if col not in df.columns:
            df[col] = None # Pandas converterá None para NaN em colunas numéricas, ou manterá None para object
            
    df = df[final_columns_order] # Reordena/seleciona as colunas

    try:
        # Salva o DataFrame em um arquivo CSV, usando ; como separador
        df.to_csv(filename, index=False, encoding='utf-8-sig', sep=';') 
        print(f"Dados salvos com sucesso em {filename} (separador: ';')")
    except Exception as e:
        print(f"Erro ao salvar CSV: {e}")

if __name__ == '__main__':
    # Lista de termos de busca pré-definidos
    search_queries_list = [
        "Cartucho HP original", "Cartucho HP compativel", 
        "Cartucho HP 664", "Cartucho HP 662", 
    ]
    num_products_to_scrape_input = input(f"Quantos produtos você deseja raspar POR CADA TERMO DE BUSCA? (Pressione Enter para padrão: 2): ")
    num_products_per_term = int(num_products_to_scrape_input) if num_products_to_scrape_input.isdigit() and int(num_products_to_scrape_input) > 0 else 2

    all_product_data_across_searches = [] # Acumula dados de todas as buscas
    overall_start_time = time.time()

    for current_search_query in search_queries_list:
        print(f"\n======================================================================")
        print(f"PROCESSANDO TERMO DE BUSCA: '{current_search_query}'")
        print(f"======================================================================")
        
        product_links_to_scrape = []
        search_driver_instance = None
        try:
            print(f"Iniciando driver para busca de links para '{current_search_query}'...")
            search_driver_instance = setup_driver()
            product_links_to_scrape = search_mercado_livre_and_get_links(current_search_query, search_driver_instance, max_links=num_products_per_term)
        except Exception as e_search:
            print(f"Erro durante a busca de links para '{current_search_query}': {type(e_search).__name__} - {e_search}")
        finally:
            if search_driver_instance:
                print("Fechando driver da busca..."); search_driver_instance.quit(); time.sleep(random.uniform(1,2)) 

        if not product_links_to_scrape:
            print(f"Nenhum link de produto foi encontrado para '{current_search_query}'. Pulando para o próximo termo.")
            continue # Pula para o próximo termo de busca
        
        print(f"\nIniciando scraping para {len(product_links_to_scrape)} produtos encontrados para '{current_search_query}'...")
        for i, url in enumerate(product_links_to_scrape):
            print(f"\n--- Raspando Produto {i+1} de {len(product_links_to_scrape)} (Termo: '{current_search_query}'): {url} ---")
            product_driver = None 
            try:
                product_driver = setup_driver()
                # Pausa antes de carregar a URL do produto
                if i > 0 or (i == 0 and current_search_query != search_queries_list[0]): 
                    inter_product_pause = random.uniform(3, 6) 
                    print(f"Pausando por {inter_product_pause:.2f}s antes de carregar o produto...")
                    time.sleep(inter_product_pause)
                
                product_info = scrape_mercado_livre_product(url, product_driver)
                all_product_data_across_searches.append(product_info)
                
                print("\nDados coletados para este produto:")
                for key, value in product_info.items():
                    if key == 'dados_extras': continue # Não printa 'dados_extras' pois foi removido
                    print(f"  {key}: {value}")

            except Exception as e_product_scrape:
                print(f"Erro CRÍTICO ao processar o produto {url}: {type(e_product_scrape).__name__} - {e_product_scrape}")
                all_product_data_across_searches.append({'link_anuncio': url, 'titulo': 'ERRO NA COLETA', 'preco': None, 
                                                         'vendedor': None, 'avaliacao_nota': None, 'avaliacao_numero': None, 
                                                         'descricao': None, 'dados_extras': None}) # dados_extras é None
            finally:
                if product_driver:
                    print(f"Fechando navegador para produto {i+1}..."); product_driver.quit()
                # Pausa entre o fechamento de um driver de produto e a inicialização do próximo (se houver próximo)
                if i < len(product_links_to_scrape) -1 :
                    inter_driver_pause_short = random.uniform(2,4)
                    print(f"Pausa de {inter_driver_pause_short:.2f}s antes de iniciar o próximo driver de produto...")
                    time.sleep(inter_driver_pause_short)
            
        print(f"\nFim do processamento para o termo: '{current_search_query}'")
        # Pausa maior entre diferentes termos de busca
        if current_search_query != search_queries_list[-1]: # Se não for o último termo
            inter_search_term_pause = random.uniform(5, 10)
            print(f"Pausando por {inter_search_term_pause:.2f}s antes do próximo termo de busca...")
            time.sleep(inter_search_term_pause)

    # Salvar todos os dados coletados em um único CSV no final
    if all_product_data_across_searches:
        # Nome de arquivo mais genérico já que são vários termos
        filename = f"ml_produtos_hp_coletados.csv"
        save_to_csv(all_product_data_across_searches, filename)
    else:
        print("Nenhum dado de produto foi coletado de nenhuma busca para salvar.")
    
    overall_end_time = time.time()
    print(f"\n--- Processo de scraping completo. Tempo total: {(overall_end_time - overall_start_time)/60:.2f} minutos ---")