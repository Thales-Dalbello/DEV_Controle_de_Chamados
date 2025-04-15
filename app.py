from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'chave_secreta_segura'

# ----------- Banco de Dados -----------
def init_db():
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            login TEXT UNIQUE,
            senha TEXT,
            perfil TEXT
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            titulo TEXT,
            descricao TEXT,
            prioridade TEXT,
            status TEXT DEFAULT 'Aberto',
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
        ''')
        # Cria usuário master padrão
        cursor.execute("SELECT * FROM usuarios WHERE login = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO usuarios (nome, login, senha, perfil) VALUES (?, ?, ?, ?)",
                           ("Administrador", "admin", generate_password_hash("admin123"), "master"))
        conn.commit()

# ----------- Rotas -----------
@app.route("/")
def index():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form["login"]
        senha = request.form["senha"]
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE login = ?", (login,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user[3], senha):
            session["usuario_id"] = user[0]
            session["nome"] = user[1]
            session["perfil"] = user[4]
            return redirect("/dashboard")
        else:
            return "Login inválido!"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
def dashboard():
    if "usuario_id" not in session:
        return redirect("/login")
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if session["perfil"] == "master":
        cursor.execute("SELECT c.id, u.nome, c.titulo, c.prioridade, c.status FROM chamados c JOIN usuarios u ON c.usuario_id = u.id")
    else:
        cursor.execute("SELECT id, titulo, prioridade, status FROM chamados WHERE usuario_id = ?", (session["usuario_id"],))
    
    chamados = cursor.fetchall()
    conn.close()
    return render_template("dashboard.html", chamados=chamados)

@app.route("/abrir_chamado", methods=["GET", "POST"])
def abrir_chamado():
    if "usuario_id" not in session:
        return redirect("/login")
    
    if request.method == "POST":
        titulo = request.form["titulo"]
        descricao = request.form["descricao"]
        prioridade = request.form["prioridade"]
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chamados (usuario_id, titulo, descricao, prioridade) VALUES (?, ?, ?, ?)",
                       (session["usuario_id"], titulo, descricao, prioridade))
        conn.commit()
        conn.close()
        return redirect("/dashboard")
    
    return render_template("abrir_chamado.html")

@app.route("/atualizar_status/<int:id>/<novo_status>")
def atualizar_status(id, novo_status):
    if session.get("perfil") != "master":
        return "Acesso negado."
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE chamados SET status = ? WHERE id = ?", (novo_status, id))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ----------- Iniciar App -----------
import os

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
