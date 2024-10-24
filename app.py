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
    user_data = result.data[0] if result.data else None
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

# Ruta para subir película
@app.route('/subir_pelicula', methods=['GET', 'POST'])
@login_required
def subir_pelicula():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        
        # Inserta la película en la base de datos
        result = client.table('Peliculas').insert({
            'titulo': titulo,
            'descripcion': descripcion,
            'moderador_id': current_user.id  # El usuario actual que está subiendo la película
        }).execute()

        if result:
            flash('Película subida exitosamente', 'success')
        else:
            flash('Error al subir la película', 'danger')

        return redirect(url_for('home'))
    
    return render_template('subir_pelicula.html')

# Ruta para la página principal (protegida)
@app.route('/')
@login_required
def home():
    peliculas = client.table('Peliculas').select('*').execute().data
    return render_template('home.html', peliculas=peliculas)

# Ruta para ver los detalles de una película
@app.route('/pelicula/<int:pelicula_id>', methods=['GET'])
def ver_pelicula(pelicula_id):
    # Obtener la película
    pelicula = client.table('Peliculas').select('*').eq('id', pelicula_id).execute().data[0]

    # Obtener los comentarios con la información del usuario
    comentarios_query = """
    SELECT Comentarios.comentario, Comentarios.fecha, Usuarios.email as usuario_email
    FROM Comentarios
    JOIN Usuarios ON Comentarios.usuario_id = Usuarios.id
    WHERE Comentarios.pelicula_id = %s
    """
    comentarios = client.rpc('run_sql', {'sql': comentarios_query % pelicula_id}).execute().data

    return render_template('ver_pelicula.html', pelicula=pelicula, comentarios=comentarios)


# Ruta para comentar en una película
@app.route('/pelicula/<int:pelicula_id>/comentar', methods=['POST'])
@login_required
def comentar(pelicula_id):
    comentario = request.form['comentario']
    
    client.table('Comentarios').insert({
        'comentario': comentario,
        'pelicula_id': pelicula_id,
        'usuario_id': current_user.id
    }).execute()
    
    return redirect(url_for('ver_pelicula', pelicula_id=pelicula_id))

@app.route('/comentario/<int:comentario_id>/eliminar', methods=['POST'])
@login_required
def eliminar_comentario(comentario_id):
    comentario = client.table('Comentarios').select('*').eq('id', comentario_id).execute().data[0]

    # Solo el usuario que hizo el comentario puede eliminarlo
    if comentario['usuario_id'] != current_user.id:
        flash("No tienes permiso para eliminar este comentario.", "danger")
        return redirect(url_for('home'))

    client.table('Comentarios').delete().eq('id', comentario_id).execute()
    flash("Comentario eliminado exitosamente.", "success")
    return redirect(url_for('ver_pelicula', pelicula_id=comentario['pelicula_id']))


# Ruta para cerrar sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión.", "success")
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
