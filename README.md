
# Análise de Tintas para Impressoras HP (Fase 2)

## 1. Visão Geral do Projeto

Este projeto corresponde à segunda fase de uma análise de mercado focada nos suprimentos para impressoras HP. O grupo buscou aprofundar os resultados obtidos anteriormente, com ênfase em uma coleta de dados mais abrangente e uma análise exploratória mais robusta.

Nesta nova etapa, as melhorias se concentraram em dois eixos principais:

- **Expansão e Otimização do Coletor de Dados**: O sistema de web scraping foi reestruturado para funcionar de forma integrada em diferentes plataformas de e-commerce. Abandonou-se o uso de scripts isolados em favor de uma abordagem unificada (`scraping_unificado.py`), com mecanismos de alternância de agentes de navegação e simulação de comportamento humano para mitigar bloqueios automatizados.

- **Enriquecimento e Visualização Analítica**: Após a coleta, os dados foram limpos e enriquecidos com informações estratégicas — como compatibilidade, custo por página e tipo de cartucho —, culminando em um conjunto de gráficos que facilitam a tomada de decisão com base em preço, qualidade e custo-benefício.

## 2. Ferramentas e Bibliotecas Utilizadas

Para viabilizar a coleta e análise de dados, o grupo utilizou as seguintes tecnologias dentro do ecossistema Python:

- **Python 3.12**
- **Selenium**: Para navegação automatizada e raspagem de dados.
- **Pandas**: Manipulação e estruturação da base de dados.
- **Matplotlib & Seaborn**: Geração de gráficos e visualizações.
- **webdriver-manager**: Gerenciamento de drivers de navegador.
- **re (Regex)**: Processamento de texto, especialmente para normalização de preços.

## 3. Estrutura e Execução do Projeto

A arquitetura do projeto foi consolidada em dois arquivos principais:

### Script 1: `scraping_unificado.py` (Coletor de Dados Unificado)

Este script realiza o scraping nas plataformas Mercado Livre e Magazine Luiza. Ele executa a coleta de forma sequencial, alternando automaticamente os parâmetros de navegação para simular usuários distintos (user-agents e tempos de espera aleatórios).

O resultado da coleta é salvo em um arquivo CSV padronizado:  
📄 `dados_enriquecidos_analise.csv`

### Script 2: `analise.py` (Análise e Visualização de Dados)

Este script é responsável por toda a parte analítica:

- Leitura e padronização do CSV gerado na etapa anterior;
- Criação de colunas derivadas de valor analítico (ex: custo por página, tipo de cartucho, compatibilidade);
- Geração de quatro gráficos com foco em padrões de consumo, preço, avaliação e custo-benefício.

---

### Como Usar o Projeto

**1. Instale as dependências:**

```bash
pip install -r requirements.txt
```

**2. Execute a raspagem de dados:**

```bash
python scraping_unificado.py
```

O script solicitará quantos produtos devem ser coletados por termo de busca.

**3. Execute a análise e geração dos gráficos:**

```bash
python analise.py
```

Os gráficos serão salvos automaticamente na pasta do projeto.

---

## 4. Principais Desafios e Soluções

### 4.1. Mecanismos Anti-Bot e Estratégias de Mitigação

A intenção inicial era incluir a plataforma KaBuM! no escopo da coleta. No entanto, as barreiras automatizadas de segurança impediram o acesso contínuo às páginas de produto.

**Solução:** A equipe optou por redirecionar os esforços para a Magazine Luiza e aprimorar a simulação de comportamento humano por meio de:

- Alternância de **user-agents**;
- Rolagens suaves e movimentos simulados do mouse;
- Tempos de espera randômicos entre as ações.

### 4.2. Comparação de Métricas com Escalas Diferentes

Para permitir a comparação entre métricas com escalas diferentes (ex: número de avaliações vs. nota média), foi aplicada a **normalização Min-Max**, reescalando todos os valores entre 0 e 1.

---

## 5. Análise dos Resultados

### Gráfico 1: Distribuição de Preços

<!-- placeholder imagem -->
![grafico_1_preco_vs_compatibilidade](caminho/para/grafico_1_preco_vs_compatibilidade.png)

**Análise:**
- Cartuchos **originais** apresentam preços mais altos e dispersos.
- Cartuchos **compatíveis** concentram-se em uma faixa mais estreita e acessível.
- Os preços foram interpretados conforme normalizados, devido à ausência de separador decimal em algumas fontes.

---

### Gráfico 2: Preço vs. Nota de Avaliação

<!-- placeholder imagem -->
![grafico_2_preco_vs_avaliacao](caminho/para/grafico_2_preco_vs_avaliacao.png)

**Análise:**
- Não há uma correlação clara entre preço e satisfação.
- Vários produtos acessíveis possuem notas elevadas (acima de 4.5).

---

### Gráfico 3: Popularidade vs. Qualidade por Modelo

<!-- placeholder imagem -->
![grafico_3_popularidade_vs_qualidade](caminho/para/grafico_3_popularidade_vs_qualidade.png)

**Análise:**
- **Modelo 667** possui nota máxima, mas menor volume de avaliações.
- **Modelo 664** lidera em popularidade com qualidade igualmente elevada.

---

### Gráfico 4: Top 15 Produtos com Melhor Custo-Benefício

<!-- placeholder imagem -->
![grafico_4_custo_beneficio](caminho/para/grafico_4_custo_beneficio.png)

**Análise:**
- Cartuchos **XL (alto rendimento)** figuram entre os produtos com menor custo por página.
- A combinação entre avaliação, preço e rendimento revelou oportunidades de melhor escolha para o consumidor final.

---

Este projeto reforça a importância de decisões baseadas em dados reais de mercado, demonstrando como a coleta automatizada, aliada à análise visual, pode contribuir para a compreensão de dinâmicas de consumo em nichos altamente competitivos.
