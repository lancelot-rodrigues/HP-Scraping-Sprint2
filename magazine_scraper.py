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
from selenium.webdriver.common.action_chains import ActionChains

# ========== Configuração do WebDriver ==========

from driver_config import setup_driver

# ========== Funções auxiliares ==========
def clean_price(price_str):
    if not price_str: return None
    s = str(price_str).lower().strip()
    s = re.sub(r'\.(?=\d{3}(?:,|\sreais|$))', '', s)
    match = re.search(r'([\d,]+)\s*reais(?:\s*(?:e|,|com)\s*([\d,]+)\s*centavos)?', s)
    if match:
        reais = match.group(1).replace(',', '')
        centavos = match.group(2)
        try:
            if centavos:
                return float(f"{int(reais)}.{int(centavos):02d}")
            return float(reais)
        except ValueError:
            return None
    s = re.sub(r'\s*reais?$', '', s)
    if s.startswith("r$"): s = s[2:]
    s = re.sub(r'\.(?=\d{3}(?:,|$))', '', s)
    s = s.replace(',', '.')
    s = re.sub(r'[^\d\.]', '', s)
    try:
        return float(s)
    except ValueError:
        return None

def extract_review_count(text):
    if not text: return None
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else None

# ========== Scraper Magazine Luiza ==========
def simulate_human_behavior(driver):
    try:
        actions = ActionChains(driver)
        body = driver.find_element(By.TAG_NAME, 'body')
        actions.move_to_element_with_offset(body, random.randint(100, 300), random.randint(100, 300)).perform()
        time.sleep(random.uniform(0.5, 1.5))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.25);")
        time.sleep(random.uniform(1.0, 2.0))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.75);")
        time.sleep(random.uniform(1.0, 2.0))
        driver.execute_script("window.scrollTo(0, 0);")
    except:
        pass

def search_magalu_and_get_links(search_term, driver, max_links=10):
    url = f"https://www.magazineluiza.com.br/busca/{search_term.replace(' ', '%20')}/"
    driver.get(url)
    time.sleep(random.uniform(4, 6))
    simulate_human_behavior(driver)

    links = set()
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '/produto/') or @data-testid='product-card-container']"))
        )
        elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/produto/') or @data-testid='product-card-container']")
        for el in elements:
            href = el.get_attribute('href')
            if href:
                href = href.split('?')[0]
                if href not in links:
                    links.add(href)
                    if len(links) >= max_links: break
    except Exception as e:
        print(f"Erro ao coletar links Magalu: {e}")
    return list(links)

def scrape_magalu_product(url, driver):
    driver.get(url)
    simulate_human_behavior(driver)
    time.sleep(random.uniform(3, 5))
    wait = WebDriverWait(driver, 15)
    data = {'link_anuncio': url}

    try: data['titulo'] = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1[data-testid='heading-product-title']"))).text.strip()
    except: data['titulo'] = None

    try: data['preco'] = clean_price(wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p[data-testid='price-value']"))).text)
    except: data['preco'] = None

    try:
        vendedor_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='seller-info-label']")))
        data['vendedor'] = vendedor_el.text.strip().replace("Vendido e entregue por", "").strip()
    except: data['vendedor'] = "Magazine Luiza"

    try:
        score = driver.find_element(By.XPATH, "//span[@format='score-count']").text.strip()
        nota_match = re.search(r'(\d+(\.\d+)?)', score)
        qtd_match = re.search(r'\((\d+)\)', score)
        data['avaliacao_nota'] = nota_match.group(1) if nota_match else None
        data['avaliacao_numero'] = int(qtd_match.group(1)) if qtd_match else None
    except: data['avaliacao_nota'], data['avaliacao_numero'] = None, None

    try:
        desc_el = driver.find_element(By.CSS_SELECTOR, "div[data-testid='product-detail-description']")
        data['descricao'] = re.sub(r'\s+', ' ', desc_el.text).strip()
    except: data['descricao'] = None

    return data

# ========== Salvamento ==========
def save_to_csv(data, filename):
    if not data:
        print("Nenhum dado a salvar.")
        return
    df = pd.DataFrame(data)
    cols = ['plataforma', 'link_anuncio', 'titulo', 'preco', 'vendedor', 'avaliacao_nota', 'avaliacao_numero', 'descricao']
    for col in cols:
        if col not in df.columns:
            df[col] = None
    df = df[cols]
    df.to_csv(filename, index=False, encoding='utf-8-sig', sep=';')
    print(f"Dados salvos em: {filename}")

# ========== Execução ==========
if __name__ == '__main__':
    queries = [
        "Cartucho HP original", "Cartucho HP compativel",
        "Cartucho HP 664", "Cartucho HP 662"
    ]
    num = input("Quantos produtos por termo? (Enter para 2): ")
    num = int(num) if num.isdigit() and int(num) > 0 else 2
    data = []
    start = time.time()

    print(f"\n=== MAGALU ===")
    for termo in queries:
        print(f"\n>>> Termo: {termo}")
        try:
            d1 = setup_driver()
            links = search_magalu_and_get_links(termo, d1, max_links=num)
        except Exception as e:
            print(f"Erro ao buscar links: {e}")
            links = []
        finally:
            d1.quit()

        for i, url in enumerate(links):
            print(f"({i+1}/{len(links)}) Raspando: {url}")
            try:
                d2 = setup_driver()
                time.sleep(random.uniform(2, 4))
                item = scrape_magalu_product(url, d2)
                item['plataforma'] = 'magalu'
                data.append(item)
            except Exception as e:
                print(f"Erro: {e}")
            finally:
                d2.quit()
                time.sleep(random.uniform(2, 4))

    filename = f"magalu_produtos_coletados.csv"
    save_to_csv(data, filename)
    print(f"Tempo total: {(time.time() - start)/60:.2f} minutos")
