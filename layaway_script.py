
def gerar_jogos_layaway(dia):
    import pandas as pd
    import numpy as np
    import requests
    import joblib
    import urllib.request
    import io
    from io import BytesIO
    import warnings
    warnings.filterwarnings("ignore")

    def drop_reset_index(df):
        df = df.dropna()
        df = df.reset_index(drop=True)
        df.index += 1
        return df

    ODD_Max = 15.00
    alfa = 1.8015
    beta = 1.2583

    GITHUB_API_URL = "https://api.github.com/repos"
    OWNER = "futpythontrader"
    REPO = "FutPythonTrader"
    TOKEN = "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"

    file_path = f"Jogos_do_Dia/Betfair/Jogos_do_Dia_Betfair_Back_Lay_{dia}.csv"
    url = f"{GITHUB_API_URL}/{OWNER}/{REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {TOKEN}"}

    response = requests.get(url, headers=headers)
    data = response.json()
    download_url = data['download_url']
    content = requests.get(download_url, headers=headers).content
    lista = pd.read_csv(io.BytesIO(content))
    lista = drop_reset_index(lista)

    try:
        lista = pd.read_csv(download_url)
    except Exception as e:
        print(f"Erro ao carregar o arquivo: {e}")
        return

    df = lista[["League", "Date", "Time", "Home", "Away", "Odd_H_Back", "Odd_D_Back", "Odd_A_Back", "Odd_H_Lay", "Odd_D_Lay", "Odd_A_Lay"]]
    df.columns = ["Liga", "Data", "Hora", "Home", "Away", "Odd_H", "Odd_D", "Odd_A", "Odd_H_Lay", "Odd_D_Lay", "Odd_A_Lay"]
    df = df.sort_values(by="Hora")
    df = drop_reset_index(df)
    df = df[((df['Odd_A_Lay'] >= 2.00) & (df['Odd_A_Lay'] <= ODD_Max)) & (df['Odd_H'] < df['Odd_A'])]
    df = drop_reset_index(df)

    jogos = df.copy()
    jogos.replace(np.inf, 1, inplace=True)
    jogos.dropna(inplace=True)
    jogos.reset_index(inplace=True, drop=True)
    jogos.index = jogos.index.set_names(['Nº'])
    jogos = jogos.rename(index=lambda x: x + 1)

    prob_H = round(1 / jogos['Odd_H'], 4)
    prob_D = round(1 / jogos['Odd_D'], 4)
    prob_A = round(1 / jogos['Odd_A'], 4)
    DP = jogos[['Odd_H', 'Odd_D', 'Odd_A']].std(axis=1)
    media = jogos[['Odd_H', 'Odd_D', 'Odd_A']].mean(axis=1)
    CV_Odds = DP / media

    jogos['VAR1'] = round((prob_H + prob_D), 4)
    jogos['VAR2'] = round(1 / (1 + (alfa * ((jogos['Odd_A'] / jogos['Odd_D'])**beta))), 4)
    jogos['VAR3'] = np.round(CV_Odds, 4)
    jogos['VAR4'] = np.round(np.log(jogos['Odd_A'] / jogos['Odd_H']), 4)

    url = 'https://github.com/tuedoidoe/Previsao_Entrada/raw/refs/heads/main/Dados_Excel/Modelo_LayAway_3.0.pkl'
    caminho_arquivo = 'Modelo_LayAway_3.0.pkl'
    urllib.request.urlretrieve(url, caminho_arquivo)

    model = joblib.load(caminho_arquivo)

    X_today = jogos[['VAR2','VAR3','VAR4']]

    if X_today.empty:
        entrada = pd.DataFrame()
    else:
        jogos['Lay_Away'] = model.predict(X_today)

        jogos = jogos[
            (jogos['VAR3'] > 0.6017) &
            ((jogos['VAR2'] > 0.1595) & (jogos['VAR2'] < 0.3030)) &
            (jogos['VAR4'] >= 1.54) &
            (
                jogos['Odd_A'].between(6.00, 7.00) |
                jogos['Odd_A'].between(8.00, 9.50) |
                jogos['Odd_A'].between(10.00, 12.50) |
                jogos['Odd_A'].between(13.50, 15.00)
            )
        ]
        jogos = drop_reset_index(jogos)

        resultado = jogos[['Liga', 'Data', 'Hora', 'Home', 'Away', 'Odd_H_Lay', 'Odd_D_Lay', 'Odd_A_Lay', 'Lay_Away']]
        resultado['Lay_Away'] = pd.to_numeric(resultado['Lay_Away'], errors='coerce')
        entrada = resultado[resultado['Lay_Away'] == 1]
        entrada = drop_reset_index(entrada)

    try:
        entrada["Atualizado_em"] = pd.Timestamp.now()
        entrada.to_csv("data/resultados.csv", index=False)
    except:
        df = pd.DataFrame([{"Mensagem": "Sem resultados para o dia selecionado", "Atualizado_em": pd.Timestamp.now()}])
        df.to_csv("data/resultados.csv", index=False)
