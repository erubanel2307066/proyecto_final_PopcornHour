from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from supabase import create_client, Client
from models.models import User


app = Flask(__name__)
app.secret_key = "tu_secreto_super_secreto"

# Configuración de Supabase
supabase_url = "https://druqkagvgwrsordpmgnb.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRydXFrYWd2Z3dyc29yZHBtZ25iIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mjk2NDIzOTgsImV4cCI6MjA0NTIxODM5OH0.RVH4k-D5C2iIdcfxISQZq6lnGRDBBeoAQDvhFoWjuvc"
client: Client = create_client(supabase_url, supabase_key)

# Configuración de Flask-Login y Bcrypt
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Cargar usuario
@login_manager.user_loader
def load_user(user_id):
    result = client.table('Usuarios').select('*').eq('id', user_id).execute()
    user_data = result.data[0]
    if user_data:
        return User(user_data['id'], user_data['email'], user_data['password_hash'])
    return None

# Ruta para registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        password_hash = User.hash_password(password)

        # Verificar si el correo ya existe
        existing_user = client.table('Usuarios').select('*').eq('email', email).execute().data
        if existing_user:
            flash("El correo ya está registrado.", "danger")
            return redirect(url_for('register'))

        # Crear nuevo usuario
        client.table('Usuarios').insert({'email': email, 'password_hash': password_hash}).execute()
        flash("Registro exitoso. Por favor, inicia sesión.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

# Ruta para inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Buscar el usuario por correo electrónico
        result = client.table('Usuarios').select('*').eq('email', email).execute()
        user_data = result.data
        if user_data:
            user = User(user_data[0]['id'], user_data[0]['email'], user_data[0]['password_hash'])
            if user.check_password(password):
                login_user(user)
                flash("Inicio de sesión exitoso.", "success")
                return redirect(url_for('home'))
            else:
                flash("Contraseña incorrecta.", "danger")
        else:
            flash("El usuario no existe.", "danger")
    return render_template('login.html')

# Ruta para cerrar sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión.", "success")
    return redirect(url_for('login'))

# Ruta para la página principal (protegida)
@app.route('/')
@login_required
def home():
    peliculas = client.table('Peliculas').select('*').execute().data
    return render_template('home.html', peliculas=peliculas)

if __name__ == "__main__":
    app.run(debug=True)
