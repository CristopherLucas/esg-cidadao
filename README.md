# ESG Cidadão — fonte de dados

Este repositório é a **fonte de dados** do app ESG Cidadão: um ETL em Python
que transforma os dados abertos da CVM e da B3 num JSON enxuto, publicado por
HTTPS e atualizado automaticamente toda semana.

O código do aplicativo Android não fica aqui.

## O dado publicado

```
https://cristopherlucas.github.io/esg-cidadao/data/esg-data.json
```

Contém, para cada empresa, o veredito em três dimensões — Ambiental, Social e
Governança — e os indicadores que o originaram, cada um com valor, comparação
setorial e a fonte oficial.

## De onde vem

| Fonte | O que fornece |
|---|---|
| [Formulário de Referência da CVM](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre) | diversidade de gênero, raça e PCD; remuneração; comitês; transações com partes relacionadas; relações familiares |
| [Cadastro de companhias abertas da CVM](https://dados.cvm.gov.br/dataset/cia_aberta-cad) | razão social, CNPJ, setor e situação do registro |
| [Carteira ISE B3 2026](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-sustentabilidade/) | selo de sustentabilidade, base da dimensão Ambiental |

## Metodologia

Cada indicador vira um **percentil dentro do próprio setor**: a fração de
empresas do setor em situação pior. A pontuação da dimensão é a média dos
percentis; o semáforo sai daí — verde acima de 66, amarelo de 33 a 65,
vermelho abaixo de 33.

Três regras impedem que se produza veredito sem base:

- **Mínimo de 3 pares** para posicionar um indicador. Abaixo disso ele aparece
  com valor e fonte, mas sem percentil e fora do cálculo — senão uma empresa
  sozinha seria comparada consigo mesma e receberia sempre zero.
- **Mínimo de 2 indicadores** posicionados por dimensão, senão ela fica
  `SEM_DADOS` em vez de receber um amarelo inventado.
- **Booleanos valem 100 ou 0, em absoluto.** Ter comitê de auditoria é um
  fato, não uma posição: como 84% das companhias têm, o percentil relativo
  daria 16 a quem tem, punindo quem cumpre a boa prática.

## Atualização automática

O workflow [`atualizar-dados.yml`](.github/workflows/atualizar-dados.yml) roda
toda segunda-feira: baixa os datasets da CVM, executa a suíte de testes,
regenera o JSON e só então commita. Se o dataset resultante vier com menos de
30 empresas — sinal de que a CVM mudou o layout dos CSVs — ele aborta sem
publicar.

## Rodar localmente

```bash
cd etl
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest          # 63 testes
.venv/bin/python -m esg_etl.build   # gera docs/data/esg-data.json
```

## Limitações

1. **Só companhias abertas brasileiras** — 662 ativas na CVM, das quais 51 têm
   marca curada. Nestlé, Unilever e Procter & Gamble não aparecem.
2. **A dimensão Ambiental é fraca.** A CVM não publica emissões, água ou
   resíduos em formato estruturado, então ela se apoia num único sinal
   binário. A ausência do selo vira `SEM_DADOS`, nunca vermelho.
3. **Dados anuais.** O Formulário de Referência é entregue uma vez por
   exercício.
4. **O percentil é relativo.** Verde significa "melhor que os pares do setor",
   não "bom em termos absolutos".

Dados da CVM e da B3, de acesso público. Este repositório não tem vínculo com
nenhuma das duas instituições.
