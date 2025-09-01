from flask import Flask, render_template, request, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from layaway_script import gerar_jogos_layaway
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import threading
import time

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

login_manager = LoginManager()
login_manager.init_app(app)

USUARIOS = {
    "tuedoidoe": "Forta2006",
    "usuario": "use2807"
}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route("/", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        usuario = request.form["username"]
        senha = request.form["password"]
        if usuario in USUARIOS and USUARIOS[usuario] == senha:
            login_user(User(usuario))
            return redirect("/dashboard")
        else:
            erro = "Usuário ou senha incorretos."
    return render_template("login.html", erro=erro)

def _odd_max_por_perfil(perfil: str) -> float:
    mapa = {
        "conservador": 13.0,
        "moderado": 17.0,
        "arrojado": 20.0,
    }
    return mapa.get(perfil, 13.0)  # padrão conservador

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    # Lê perfil escolhido; padrão conservador
    perfil = request.form.get("perfil", request.args.get("perfil", "conservador"))
    odd_max = _odd_max_por_perfil(perfil)

    # Lê data (se não vier, usa hoje)
    data = request.form.get("data", "")
    if request.method == "POST" and data:
        # Executa geração com a ODD_MAX do perfil escolhido
        gerar_jogos_layaway(data, odd_max=odd_max)
    elif request.method == "GET":
        data = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d")
        gerar_jogos_layaway(data, odd_max=odd_max)

    try:
        df_original = pd.read_csv("data/resultados.csv")

        # Converte carimbo de atualização (gravado em UTC) para Brasília
        ultima = df_original["Atualizado_em"].max()
        # utc=True funciona pra string com/sem tz; depois converte
        ultima = pd.to_datetime(ultima, utc=True).tz_convert('America/Sao_Paulo').strftime("%d-%m-%y %H:%M")

        # Apenas esconde colunas indesejadas na visualização (não filtra!)
        df = df_original.drop(columns=["Lay_Away", "Atualizado_em"], errors="ignore")
        df = df.rename(columns={
            "Odd_H_Lay": "Odd_Casa",
            "Odd_D_Lay": "Odd_Empate",
            "Odd_A_Lay": "Odd_Fora"
        })

        total_jogos = len(df)
        table_html = df.to_html(classes="table table-bordered table-hover align-middle", index=False, border=0)
    except Exception as e:
        print("Erro no processamento:", e)
        df = pd.DataFrame(columns=["Data", "Time", "Odd_Casa", "Odd_Empate", "Odd_Fora"])
        ultima = "Sem dados"
        total_jogos = 0
        table_html = df.to_html(classes="table table-bordered table-hover align-middle", index=False, border=0)

    return render_template(
        "dashboard.html",
        table=table_html,
        last_update=ultima,
        total_jogos=total_jogos,
        perfil=perfil
    )

@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")

def auto_update():
    # Atualiza sozinho em HH:05 com ODD_MAX padrão (conservador)
    while True:
        agora = datetime.now(ZoneInfo("America/Sao_Paulo"))

        proxima_hora = agora.replace(minute=5, second=0, microsecond=0)
        if agora.minute >= 5:
            proxima_hora = proxima_hora.replace(hour=agora.hour + 1)
            if proxima_hora.hour == 24:
                proxima_hora = proxima_hora.replace(hour=0)

        tempo_espera = (proxima_hora - agora).total_seconds()
        print(f"Aguardando até {proxima_hora.strftime('%H:%M')} para atualizar LayAway...")

        time.sleep(tempo_espera)

        try:
            hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d")
            print(f"Atualizando jogos às {datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%H:%M:%S')}...")
            gerar_jogos_layaway(hoje, odd_max=13.0)  # conservador como padrão
        except Exception as e:
            print("Erro ao atualizar automaticamente:", e)

if __name__ == "__main__":
    threading.Thread(target=auto_update, daemon=True).start()
    app.run(debug=True)

