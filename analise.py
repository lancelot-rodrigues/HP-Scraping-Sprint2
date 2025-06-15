import pandas as pd
import re
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.ticker import FuncFormatter

# Etapa 0: Configuração de Estilo para os Gráficos
def setup_visual_style():
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (12, 7)
    plt.rcParams['axes.titlesize'] = 18
    plt.rcParams['axes.labelsize'] = 14
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12
    plt.rcParams['figure.dpi'] = 100

# Etapa 1: Leitura e Limpeza dos Dados
def load_and_clean_data(filepath):
    """Carrega o CSV e realiza a limpeza dos dados numéricos."""
    print("Iniciando a leitura e limpeza dos dados...")
    try:
        df = pd.read_csv(filepath, sep=';')
    except FileNotFoundError:
        print(f"Erro: Arquivo '{filepath}' não encontrado.")
        return None

    def parse_brazilian_price(price_str):
        if pd.isna(price_str): return np.nan
        try:
            s = str(price_str).replace('R$', '').strip()
            s = s.replace('.', '').replace(',', '.')
            return float(s)
        except (ValueError, TypeError): return np.nan

    def parse_brazilian_integer(num_str):
        if pd.isna(num_str): return np.nan
        try:
            return int(float(str(num_str).replace('.', '')))
        except (ValueError, TypeError): return np.nan

    if 'preco' in df.columns:
        df['preco'] = df['preco'].apply(parse_brazilian_price)
    if 'avaliacao_nota' in df.columns:
        df['avaliacao_nota'] = pd.to_numeric(df['avaliacao_nota'].astype(str).str.replace(',', '.'), errors='coerce')
    if 'avaliacao_numero' in df.columns:
        df['avaliacao_numero'] = df['avaliacao_numero'].apply(parse_brazilian_integer)

    df.dropna(subset=['preco', 'titulo'], inplace=True)
    
    print("Limpeza concluída.")
    return df

# Etapa 2: Enriquecimento da Base de Dados
def enrich_data(df):
    """Cria novas colunas analíticas para aprofundar a análise."""
    print("\nIniciando o enriquecimento dos dados...")

    def categorize_product(title):
        title_lower = title.lower()
        if 'notebook' in title_lower or 'laptop' in title_lower:
            return 'Notebook'
        if 'impressora' in title_lower:
            return 'Impressora'
        return 'Suprimento de Impressão'
    df['categoria_produto'] = df['titulo'].apply(categorize_product)

    df['compatibilidade'] = np.where(df['titulo'].str.contains('compativel', case=False, na=False), 'Compatível', 'Original')
    df['capacidade'] = np.where(df['titulo'].str.contains('XL', case=False, na=False), 'XL (Alto Rendimento)', 'Padrão')
    df['modelo_cartucho'] = df['titulo'].str.extract(r'\b(662|664|667|954|122)\b', expand=False).fillna('Outro')
    
    def extract_yield(text):
        if not isinstance(text, str): return np.nan
        match = re.search(r'(\d+)\s*p[aá]ginas', text, re.IGNORECASE)
        return int(match.group(1)) if match else np.nan
    df['rendimento_paginas'] = df['descricao'].apply(extract_yield)
    
    df['custo_por_pagina'] = np.where(df['rendimento_paginas'] > 0, df['preco'] / df['rendimento_paginas'], np.nan)
    
    print("Enriquecimento concluído.")
    return df

# Etapa 3: Análise e Geração de Gráficos
def generate_visualizations(df):
    """Gera e salva os gráficos para a análise exploratória."""
    print("\nIniciando a geração das visualizações...")

    df_suprimentos = df[df['categoria_produto'] == 'Suprimento de Impressão'].copy()
    
    price_limit = df_suprimentos['preco'].quantile(0.95)
    df_filtered_price = df_suprimentos[df_suprimentos['preco'] <= price_limit]
    
    # Gráfico 1: Análise de Preços
    plt.figure()
    sns.boxplot(x='compatibilidade', y='preco', data=df_filtered_price, hue='compatibilidade', palette='viridis', order=['Original', 'Compatível'], legend=False)
    plt.title('Distribuição de Preços de Suprimentos')
    plt.xlabel('Tipo de Cartucho')
    plt.ylabel('Preço')
    plt.tight_layout()
    plt.savefig('grafico_1_preco_vs_compatibilidade.png')
    print("Gráfico 1 salvo.")
    plt.close()

    # Gráfico 2: Relação entre Preço e Avaliação
    plt.figure()
    sns.scatterplot(x='preco', y='avaliacao_nota', hue='compatibilidade', data=df_filtered_price.dropna(subset=['avaliacao_nota']), palette='magma', s=100, alpha=0.8)
    plt.title('Relação entre Preço e Nota de Avaliação')
    plt.xlabel('Preço')
    plt.ylabel('Nota Média de Avaliação')
    plt.legend(title='Compatibilidade')
    plt.tight_layout()
    plt.savefig('grafico_2_preco_vs_avaliacao.png')
    print("Gráfico 2 salvo.")
    plt.close()

    # Gráfico 3: Popularidade vs. Qualidade
    modelo_analysis = df.groupby('modelo_cartucho').agg(
        popularidade_total=('avaliacao_numero', 'max'),
        qualidade_media=('avaliacao_nota', 'mean')
    ).sort_values(by='popularidade_total', ascending=False).dropna()
    modelo_analysis = modelo_analysis[modelo_analysis.index != 'Outro']

    modelo_analysis['Popularidade Normalizada'] = (modelo_analysis['popularidade_total'] - modelo_analysis['popularidade_total'].min()) / (modelo_analysis['popularidade_total'].max() - modelo_analysis['popularidade_total'].min())
    modelo_analysis['Qualidade Normalizada'] = (modelo_analysis['qualidade_media'] - modelo_analysis['qualidade_media'].min()) / (modelo_analysis['qualidade_media'].max() - modelo_analysis['qualidade_media'].min())

    plt.figure()
    ax = modelo_analysis[['Popularidade Normalizada', 'Qualidade Normalizada']].plot(kind='bar', width=0.8, colormap='coolwarm', alpha=0.8)
    ax.set_title('Popularidade vs. Qualidade por Modelo')
    ax.set_xlabel('Modelo do Cartucho')
    ax.set_ylabel('Valor Normalizado (0 a 1)')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    plt.legend(['Popularidade (Nº de Avaliações)', 'Qualidade (Nota Média)'])
    plt.tight_layout()
    plt.savefig('grafico_3_popularidade_vs_qualidade.png')
    print("Gráfico 3 salvo.")
    plt.close()

    # Gráfico 4: Análise de Custo-Benefício
    custo_beneficio_df = df_suprimentos.dropna(subset=['custo_por_pagina']).sort_values(by='custo_por_pagina').head(15)
    plt.figure()
    barplot = sns.barplot(x='custo_por_pagina', y='titulo', data=custo_beneficio_df, hue='capacidade', dodge=False, palette='coolwarm')
    plt.title('Top 15 Produtos com Melhor Custo-Benefício')
    plt.xlabel('Custo por Página')
    plt.ylabel('Produto')
    plt.legend(title='Capacidade')
    plt.setp(barplot.get_yticklabels(), fontsize=8)
    plt.tight_layout()
    plt.savefig('grafico_4_custo_beneficio.png')
    print("Gráfico 4 salvo.")
    plt.close()

# Etapa 7: Execução Principal
if __name__ == '__main__':
    setup_visual_style()
    
    csv_filepath = 'ecommerce_produtos_coletados.csv'
    df_cleaned = load_and_clean_data(csv_filepath)
    
    if df_cleaned is not None:
        df_enriched = enrich_data(df_cleaned.copy())
        
        print("\n--- Amostra da Tabela Enriquecida ---")
        colunas_para_exibir = [
            'plataforma', 'titulo', 'preco', 'compatibilidade', 
            'capacidade', 'modelo_cartucho', 'rendimento_paginas', 'custo_por_pagina'
        ]
        colunas_existentes = [col for col in colunas_para_exibir if col in df_enriched.columns]
        
        # O uso de to_string() é uma alternativa que não precisa da biblioteca 'tabulate'.
        print(df_enriched[colunas_existentes].head().to_string())
        
        generate_visualizations(df_enriched)
        
        print("\nAnálise concluída com sucesso!")