import pandas as pd
import re
import time
import random
from datetime import datetime
from magazine_scraper import (
    setup_driver as setup_magalu,
    search_magalu_and_get_links,
    scrape_magalu_product,
    clean_price,
    extract_review_count
)
from mercado_scraper import (
    setup_driver as setup_ml,
    search_mercado_livre_and_get_links,
    scrape_mercado_livre_product
)

# ========= Configuração =========
queries = [
    "Cartucho HP original", "Cartucho HP compativel",
    "Tinta HP", "Cartucho de tinta HP"
]
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"
]

# ========= Salvamento =========
def save_to_csv(data, filename):
    if not data:
        print("Nenhum dado coletado.")
        return
    df = pd.DataFrame(data)
    cols = ['plataforma', 'link_anuncio', 'titulo', 'preco', 'vendedor', 'avaliacao_nota', 'avaliacao_numero', 'descricao']
    for col in cols:
        if col not in df.columns:
            df[col] = None
    df = df[cols]
    df.to_csv(filename, index=False, sep=';', encoding='utf-8-sig')
    print(f"CSV salvo em: {filename}")

# ========= Execução =========
if __name__ == '__main__':
    num = input("Quantos produtos por termo de busca? (Padrão: 2): ")
    num = int(num) if num.isdigit() else 2
    all_data = []
    start_time = time.time()

    scrapers = [
        ('magalu', setup_magalu, search_magalu_and_get_links, scrape_magalu_product),
        ('mercado_livre', setup_ml, search_mercado_livre_and_get_links, scrape_mercado_livre_product)
    ]

    for plataforma, setup_func, search_func, scrape_func in scrapers:
        print(f"\n{'='*30} {plataforma.upper()} {'='*30}")
        for termo in queries:
            print(f"\n>>> Termo: {termo}")
            time.sleep(random.uniform(8, 15))  # tempo entre buscas

            try:
                driver = setup_func()
                driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": random.choice(user_agents)})
                links = search_func(termo, driver, max_links=num)
            except Exception as e:
                print(f"Erro ao buscar links: {e}")
                links = []
            finally:
                driver.quit()

            for i, link in enumerate(links):
                print(f"({i+1}/{len(links)}) Raspando: {link}")
                try:
                    driver = setup_func()
                    driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": random.choice(user_agents)})
                    time.sleep(random.uniform(3, 6))
                    item = scrape_func(link, driver)
                    item['plataforma'] = plataforma
                    all_data.append(item)
                except Exception as e:
                    print(f"Erro ao raspar produto: {e}")
                finally:
                    driver.quit()
                    time.sleep(random.uniform(8, 15))  # tempo entre produtos

    filename = f"scraping_unificado.csv"
    save_to_csv(all_data, filename)
    print(f"Processo finalizado em {(time.time() - start_time)/60:.2f} minutos")