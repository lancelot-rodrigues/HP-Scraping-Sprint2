import pandas as pd
import re
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Etapa 1: Configuração do WebDriver
def setup_driver():
    """Configura e retorna uma instância do Chrome WebDriver com opções de camuflagem."""
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-gpu') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Desativa o pop-up de notificações do navegador, que pode bloquear a interação.
    options.add_argument("--disable-notifications")

    # A linha '--headless' foi removida para que uma janela do Chrome abra.
    # Isso é essencial para evitar a detecção por alguns sistemas anti-bot.

    s = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=s, options=options)
    
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"
        })
    except Exception as e_cdp:
        print(f"Aviso: Falha ao executar comando CDP: {e_cdp}")
    return driver

# Etapa 2: Funções de Limpeza e Extração de Dados
def clean_price(price_str_original):
    """Limpa e converte uma string de preço para um valor float."""
    if not price_str_original: return None
    s = str(price_str_original).lower().strip()
    s_no_thousands = re.sub(r'\.(?=\d{3}(?:,|\sreais|$))', '', s) 
    
    match_reais_centavos = re.search(r'([\d,]+)\s*reais(?:\s*(?:e|,|com)\s*([\d,]+)\s*centavos)?', s_no_thousands)
    if match_reais_centavos:
        reais_part_str = match_reais_centavos.group(1).replace(',', '')
        centavos_part_str = match_reais_centavos.group(2)
        try:
            reais_val = int(reais_part_str)
            if centavos_part_str:
                centavos_val = int(centavos_part_str.replace(',', ''))
                return float(f"{reais_val}.{centavos_val:02d}")
            else:
                return float(reais_val)
        except ValueError:
            pass

    s = re.sub(r'\s*reais?$', '', s).strip()
    if s.startswith("r$"): s = s[2:].strip()
    s = re.sub(r'\.(?=\d{3}(?:,|$))', '', s) 
    s = s.replace(',', '.') 
    s = re.sub(r'[^\d\.]', '', s) 
    try:
        return float(s)
    except ValueError:
        return price_str_original

def extract_review_count(count_text):
    """Extrai o número de avaliações de uma string."""
    if not count_text: return None
    match = re.search(r'(\d+)', count_text) 
    return int(match.group(1)) if match else None

# Etapa 3: Funções de Scraping do Mercado Livre
def scrape_mercado_livre_product(url, driver):
    """Coleta dados de uma página de produto específica do Mercado Livre."""
    driver.get(url)
    time.sleep(random.uniform(3.5, 5.5)) 
    wait = WebDriverWait(driver, 20)
    data = {'link_anuncio': url}

    try:
        title_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'h1.ui-pdp-title')))
        data['titulo'] = title_element.text.strip()
    except Exception: data['titulo'] = None

    try:
        price_container = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ui-pdp-price__main-container span.andes-money-amount")))
        data['preco'] = clean_price(price_container.get_attribute('aria-label'))
    except Exception: data['preco'] = None

    try:
        seller_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'ui-pdp-seller__info-container')]//h3[contains(@class, 'ui-pdp-seller__nickname')]")))
        data['vendedor'] = seller_element.text.strip()
    except Exception: data['vendedor'] = "Não informado"

    try:
        rating_el = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "p.ui-review-capability__rating__average")))
        data['avaliacao_nota'] = rating_el.text.strip()
        count_el = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "p.ui-review-capability__rating__total-reviews")))
        data['avaliacao_numero'] = extract_review_count(count_el.text.strip())
    except Exception:
        data['avaliacao_nota'], data['avaliacao_numero'] = None, None

    try:
        see_more_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@data-testid='action-collapsable-target']")))
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", see_more_button)
        time.sleep(0.7)
        driver.execute_script("arguments[0].click();", see_more_button)
        time.sleep(1.5)
    except Exception:
        pass # Continua se o botão não existir ou não for clicável
    
    try:
        desc_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.ui-pdp-description__content")))
        data['descricao'] = re.sub(r'\s+', ' ', desc_container.get_attribute('innerText').strip())
    except Exception: data['descricao'] = None
        
    data['dados_extras'] = None 
    return data

def search_mercado_livre_and_get_links(search_term, driver, max_links=10):
    """Navega na busca do Mercado Livre e coleta os links dos produtos."""
    search_term_path = search_term.replace(" ", "-")
    search_term_query = search_term.replace(" ", "+")
    search_url = f"https://lista.mercadolivre.com.br/{search_term_path}"

    print(f"Navegando para a página de busca: {search_url}")
    driver.get(search_url)
    time.sleep(random.uniform(2, 4))

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ol.ui-search-layout")))
    except Exception as e:
        print(f"Container de resultados de busca não encontrado: {e}. Nenhum link será coletado.")
        return []

    product_links, seen_links = [], set()
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
    time.sleep(random.uniform(2, 4)) 

    link_elements = driver.find_elements(By.XPATH, "//a[contains(@class, 'ui-search-link')]")
    
    for link_el in link_elements:
        try:
            href = link_el.get_attribute('href')
            if href and "/MLB-" in href and href not in seen_links:
                clean_href = href.split('?')[0] 
                product_links.append(clean_href)
                seen_links.add(clean_href)
                if len(product_links) >= max_links: break
        except Exception: continue
    return product_links

# Etapa 4: Funções de Scraping da Magazine Luiza
def search_magalu_and_get_links(search_term, driver, max_links=10):
    """Navega na busca da Magazine Luiza e coleta links de produtos."""
    search_url = f"https://www.magazineluiza.com.br/busca/{search_term.replace(' ', '%20')}/"
    print(f"Navegando para a página de busca da Magazine Luiza: {search_url}")
    driver.get(search_url)
    
    product_links, seen_links = [], set()
    try:
        wait = WebDriverWait(driver, 25)
        product_link_selector = "a[data-testid='product-card-container']"
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_link_selector)))
        
        time.sleep(random.uniform(3, 5))
        
        link_elements = driver.find_elements(By.CSS_SELECTOR, product_link_selector)
        
        for el in link_elements:
            try:
                href = el.get_attribute('href')
                if href and href not in seen_links:
                    product_links.append(href.split('?')[0])
                    seen_links.add(href.split('?')[0])
                    if len(product_links) >= max_links: break
            except Exception: continue
                
        print(f"Coletados {len(product_links)} links de produtos da Magazine Luiza.")
        return product_links

    except Exception as e:
        print(f"Falha na busca da Magazine Luiza. Erro: {e}")
        return []

def scrape_magalu_product(url, driver):
    """Coleta dados de uma página de produto específica da Magazine Luiza."""
    driver.get(url)
    time.sleep(random.uniform(4, 6))
    wait = WebDriverWait(driver, 20)
    data = {'link_anuncio': url}

    try:
        data['titulo'] = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "h1[data-testid='heading-product-title']"))).text.strip()
    except Exception: data['titulo'] = None

    try:
        price_text = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "p[data-testid='price-value']"))).text
        data['preco'] = clean_price(price_text)
    except Exception: data['preco'] = None

    try:
        seller_text = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "a[data-testid='seller-info-button']"))).text
        data['vendedor'] = seller_text.replace('Vendido e entregue por ', '').strip()
    except Exception: data['vendedor'] = "Magazine Luiza"

    try:
        review_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//span[contains(@format, 'score-count')]")))
        review_text = review_element.text.strip()
        nota_match = re.search(r'(\d\.\d+)', review_text)
        count_match = re.search(r'\((\d+)\)', review_text)
        data['avaliacao_nota'] = nota_match.group(1) if nota_match else None
        data['avaliacao_numero'] = int(count_match.group(1)) if count_match else None
    except Exception:
        data['avaliacao_nota'], data['avaliacao_numero'] = None, None

    try:
        desc_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='product-detail']")))
        data['descricao'] = re.sub(r'\s+', ' ', desc_container.text.strip())
    except Exception: data['descricao'] = None
    
    data['dados_extras'] = None
    return data

# Etapa 5: Função para Salvar os Dados
def save_to_csv(data_list, filename):
    if not data_list: 
        print("Nenhum dado para salvar.")
        return
    
    df = pd.DataFrame(data_list)
    
    final_columns_order = ['plataforma', 'link_anuncio', 'titulo', 'preco', 'vendedor', 'avaliacao_nota', 'avaliacao_numero', 'descricao']
    
    for col in final_columns_order:
        if col not in df.columns:
            df[col] = None
            
    df = df[final_columns_order]

    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig', sep=';') 
        print(f"\nDados salvos com sucesso em {filename}")
    except Exception as e:
        print(f"\nErro ao salvar CSV: {e}")

# Etapa 6: Execução Principal do Script
if __name__ == '__main__':
    PLATFORM_CONFIG = {
        'mercado_livre': {
            'search_func': search_mercado_livre_and_get_links,
            'scrape_func': scrape_mercado_livre_product
        },
        'magalu': {
            'search_func': search_magalu_and_get_links,
            'scrape_func': scrape_magalu_product
        }
    }
    platforms_to_scrape = ['mercado_livre', 'magalu']
    
    search_queries_list = [
        "Cartucho HP original", "Cartucho HP compativel", 
        "Cartucho HP 664", "Cartucho HP 662", "Cartucho tinta HP"
    ]
    num_products_input = input("Quantos produtos você deseja raspar por termo de busca? (Padrão: 2): ")
    num_products_per_term = int(num_products_input) if num_products_input.isdigit() and int(num_products_input) > 0 else 2

    all_product_data = []
    overall_start_time = time.time()

    for platform_name in platforms_to_scrape:
        print(f"\n{'='*25} INICIANDO SCRAPING: {platform_name.upper()} {'='*25}")
        
        search_function = PLATFORM_CONFIG[platform_name]['search_func']
        scrape_function = PLATFORM_CONFIG[platform_name]['scrape_func']
        
        # O navegador é criado uma única vez por plataforma para manter a sessão.
        platform_driver = None 
        try:
            print(f"Iniciando navegador para {platform_name.upper()}...")
            platform_driver = setup_driver()
            
            for current_search_query in search_queries_list:
                print(f"\n--- Processando termo: '{current_search_query}' ---")
                
                product_links_to_scrape = search_function(current_search_query, platform_driver, max_links=num_products_per_term)

                if not product_links_to_scrape:
                    print(f"Nenhum link de produto foi encontrado. Pulando para o próximo termo.")
                    continue
                
                print(f"\nIniciando scraping para {len(product_links_to_scrape)} produtos encontrados...")
                for i, url in enumerate(product_links_to_scrape):
                    print(f"Raspando Produto {i+1}/{len(product_links_to_scrape)}: {url}")
                    try:
                        product_info = scrape_function(url, platform_driver)
                        product_info['plataforma'] = platform_name
                        all_product_data.append(product_info)
                        
                        print("\nDados coletados para este produto:")
                        for key, value in product_info.items():
                            if key == 'dados_extras': continue
                            print(f"  {key}: {value}")

                    except Exception as e_product_scrape:
                        print(f"Erro CRÍTICO ao processar o produto {url}: {e_product_scrape}")
                        all_product_data.append({'plataforma': platform_name, 'link_anuncio': url, 'titulo': 'ERRO NA COLETA'})
                    
                    if i < len(product_links_to_scrape) - 1:
                        time.sleep(random.uniform(3, 6))

                time.sleep(random.uniform(5, 10))

        except Exception as e_platform_process:
            print(f"Erro fatal durante o processamento da plataforma {platform_name.upper()}: {e_platform_process}")
        finally:
            if platform_driver:
                print(f"\nFechando navegador para {platform_name.upper()}...")
                platform_driver.quit()
            
    if all_product_data:
        filename = f"ecommerce_produtos_coletados.csv"
        save_to_csv(all_product_data, filename)
    else:
        print("\nNenhum dado de produto foi coletado de nenhuma busca para salvar.")
    
    overall_end_time = time.time()
    print(f"\nProcesso de scraping completo. Tempo total: {(overall_end_time - overall_start_time)/60:.2f} minutos.")