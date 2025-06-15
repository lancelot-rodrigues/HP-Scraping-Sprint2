# Análise de Tintas para Impressoras HP (Fase 2)

## 1. Visão Geral do Projeto

Este projeto representa a segunda fase de uma análise de mercado, expandindo e aprofundando os insights obtidos em uma entrega anterior. O objetivo desta etapa foi aprimorar tanto a coleta de dados quanto a profundidade da análise, focando no competitivo segmento de suprimentos para impressoras HP.

Nesta nova fase, nosso trabalho evoluiu em duas frentes principais:

- **Expansão da Coleta de Dados**: O sistema de web scraping foi aprimorado para extrair informações de uma plataforma de e-commerce adicional, a Magazine Luiza, integrando seus dados aos já coletados do Mercado Livre. Isso nos permitiu construir uma base de dados mais rica e diversificada.
- **Análise Aprofundada e Enriquecimento de Dados**: Partindo da base de dados consolidada, desenvolvemos um pipeline de análise completo. Este processo incluiu a limpeza rigorosa dos dados, o enriquecimento com novas colunas de interesse analítico (como tipo de produto, compatibilidade e custo por página) e a geração de visualizações que revelam padrões de preço, qualidade e custo-benefício no mercado.

## 2. Ferramentas e Bibliotecas Utilizadas

Para a execução desta segunda fase, consolidamos o uso do ecossistema Python com as seguintes bibliotecas:

- **Python 3.12**
- **Selenium**: Essencial para a automação da navegação e coleta de dados em ambas as plataformas.
- **Pandas**: Utilizado para toda a manipulação, limpeza e estruturação dos dados.
- **Matplotlib & Seaborn**: Para a criação e estilização dos gráficos de análise.
- **webdriver-manager**: Para o gerenciamento automático dos drivers do navegador.

## 3. Estrutura e Execução

O projeto evoluiu para uma estrutura de dois scripts principais, projetados para serem executados em sequência:

### Script 1: `app.py` (Coletor de Dados Multicanal)

Este script, aprimorado nesta fase, realiza o web scraping em múltiplas plataformas. Ele navega, busca e extrai as informações dos produtos, consolidando os resultados em um único arquivo CSV, `ecommerce_produtos_coletados.csv`.

### Script 2: `analise.py` (Pipeline de Análise e Visualização)

Este novo script é o coração da segunda entrega. Ele lê o arquivo CSV gerado e executa todo o pipeline de análise:

- Limpeza e padronização dos dados de ambas as fontes.
- Enriquecimento da base com colunas derivadas de alto valor analítico.
- Geração de quatro visualizações de dados para extrair conclusões de negócio.

### Como Executar o Projeto

Instale as dependências:

![image](https://github.com/user-attachments/assets/4fa2c27a-7aba-4bae-b7c5-b168d8793c8c)


Execute o script de coleta de dados:

![image](https://github.com/user-attachments/assets/e5b79e5c-d357-4914-bd4d-c56b5e47e151)


Após a conclusão, execute o script de análise:

![image](https://github.com/user-attachments/assets/e3d98076-10e1-47e7-bd7a-4dd711bb9ed3)


## 4. Principais Desafios e Soluções (Fase 2)

### 4.1. Defesas Anti-Bot e a Mudança de Estratégia

Nosso plano inicial era integrar a KaBuM! como segunda fonte de dados. No entanto, nos deparamos com defesas anti-bot avançadas que impediam a coleta de forma consistente. Após explorar diversas estratégias técnicas, reconhecemos que a complexidade para contornar essas barreiras excedia o escopo e o cronograma do projeto.

**Solução:** Tomamos a decisão ágil de pivotar para a Magazine Luiza. A plataforma se mostrou mais receptiva à automação, permitindo-nos focar no objetivo principal: a análise integrada dos dados.

### 4.2. Visualização de Métricas com Escalas Diferentes

Um desafio técnico surgiu ao tentar comparar visualmente a **Popularidade** (milhares de avaliações) com a **Qualidade** (nota de 1 a 5). A discrepância de escalas tornava os gráficos combinados inúteis.

**Solução:** Aplicamos a técnica de **Normalização Min-Max**, reescalando ambas as métricas para o intervalo comum (0 a 1), permitindo uma comparação justa entre as variáveis.

## 5. Análise dos Resultados

### Gráfico 1: Distribuição de Preços

![grafico_1_preco_vs_compatibilidade](https://github.com/user-attachments/assets/73c4bc90-e01f-4d5d-9438-add23a7b2828)


**Análise:**

- O gráfico confirma a estratégia de segmentação do mercado.
- **Originais**: Possuem preço mediano e dispersão visivelmente maiores.
- **Compatíveis**: Alternativa de baixo custo, com preços mais concentrados.

---

### Gráfico 2: Relação entre Preço e Nota de Avaliação

![grafico_2_preco_vs_avaliacao](https://github.com/user-attachments/assets/cb844ced-f5d0-4603-8cb1-8bf8280e691e)


**Análise:**

- Não há correlação clara entre preço e satisfação.
- Produtos em todas as faixas de preço alcançam notas altas (4.5 a 5.0).
- Qualidade não está necessariamente ligada a preço premium.

---

### Gráfico 3: Popularidade vs. Qualidade por Modelo

![grafico_3_popularidade_vs_qualidade](https://github.com/user-attachments/assets/58da16b7-17e0-44a5-a05b-da39dc217063)


**Análise:**

- **Modelo 664**: Líder em popularidade com qualidade excelente.
- **Modelo 667**: Nota máxima de qualidade, mas menor popularidade.

**Insight Estratégico:** Há uma oportunidade em entender por que o modelo 667, o mais bem avaliado, não é o mais vendido.

---

### Gráfico 4: Análise de Custo-Benefício

![grafico_4_custo_beneficio](https://github.com/user-attachments/assets/257907a1-b168-4112-9ce1-e06850838427)


**Análise:**

- **Cartuchos XL** dominam o custo-benefício.
- Apesar de mais caros, são mais econômicos a longo prazo (baixo custo por página).
