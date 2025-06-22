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

USUARIOS = {"tuedoidoe": "Forta2006"}

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

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    data = request.form.get("data", "")
    if request.method == "POST" and data:
        gerar_jogos_layaway(data)

    try:
        df_original = pd.read_csv("data/resultados.csv")

        # Converter UTC para horário de Brasília
        ultima = df_original["Atualizado_em"].max()
        ultima = pd.to_datetime(ultima).tz_localize('UTC').tz_convert('America/Sao_Paulo').strftime("%d-%m-%y %H:%M")

        # Copiar e limpar as colunas para exibição
        df = df_original.drop(columns=["Lay_Away", "Atualizado_em"], errors="ignore")
        df = df.rename(columns={
            "Odd_H_Lay": "Odd_Casa",
            "Odd_D_Lay": "Odd_Empate",
            "Odd_A_Lay": "Odd_Fora"
        })

        total_jogos = len(df)
        table_html = df.to_html(classes="table table-bordered table-hover align-middle", index=False, border=0)
    except:
        df = pd.DataFrame(columns=["Data", "Time", "Odd_Casa", "Odd_Empate", "Odd_Fora"])
        ultima = "Sem dados"
        total_jogos = 0
        table_html = df.to_html(classes="table table-bordered table-hover align-middle", index=False, border=0)

    return render_template("dashboard.html", table=table_html, last_update=ultima, total_jogos=total_jogos)

@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")

def auto_update():
    while True:
        agora = datetime.now(ZoneInfo("America/Sao_Paulo"))

        # Calcula o próximo horário do tipo HH:05
        proxima_hora = agora.replace(minute=5, second=0, microsecond=0)
        if agora.minute >= 5:
            proxima_hora = proxima_hora.replace(hour=agora.hour + 1)
            if proxima_hora.hour == 24:
                proxima_hora = proxima_hora.replace(hour=0)  # vira meia-noite

        tempo_espera = (proxima_hora - agora).total_seconds()

        print(f"Aguardando até {proxima_hora.strftime('%H:%M')} para atualizar LayAway...")

        time.sleep(tempo_espera)

        try:
            hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d")
            print(f"Atualizando jogos às {datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%H:%M:%S')}...")
            gerar_jogos_layaway(hoje)
        except Exception as e:
            print("Erro ao atualizar automaticamente:", e)

if __name__ == "__main__":
    threading.Thread(target=auto_update, daemon=True).start()
    app.run(debug=True)
