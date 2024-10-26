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
    # Asegúrate de que el nombre de la tabla coincide exactamente con el de tu base de datos
    result = client.table('usuarios').select('*').eq('id', user_id).execute()
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
        existing_user = client.table('usuarios').select('*').eq('email', email).execute().data
        if existing_user:
            flash("El correo ya está registrado.", "danger")
            return redirect(url_for('register'))

        # Crear nuevo usuario
        client.table('usuarios').insert({'email': email, 'password_hash': password_hash}).execute()
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
        result = client.table('usuarios').select('*').eq('email', email).execute()
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

# Ruta para la página principal (protegida)
@app.route('/')
@login_required
def home():
    peliculas = client.table('peliculas').select('*').execute().data
    return render_template('home.html', peliculas=peliculas)

# Ruta para subir película
@app.route('/subir_pelicula', methods=['GET', 'POST'])
@login_required
def subir_pelicula():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        
        # Inserta la película en la base de datos
        result = client.table('peliculas').insert({
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

# Ruta para ver los detalles de una película
@app.route('/pelicula/<int:pelicula_id>', methods=['GET'])
def ver_pelicula(pelicula_id):
    # Obtener la película
    pelicula = client.table('peliculas').select('*').eq('id', pelicula_id).execute().data[0]

    # Obtener la calificación promedio
    calificaciones = client.table('calificaciones').select('calificacion').eq('pelicula_id', pelicula_id).execute().data
    if calificaciones:
        calificacion_promedio = sum([c['calificacion'] for c in calificaciones]) / len(calificaciones)
        calificacion_promedio = round(calificacion_promedio, 2)  # Redondear a 2 decimales
    else:
        calificacion_promedio = "Sin calificaciones"

    # Obtener los comentarios con la información del usuario
    comentarios = client.rpc('obtener_comentarios_con_usuario', {'pelicula_id': pelicula_id}).execute().data

    return render_template('ver_pelicula.html', pelicula=pelicula, comentarios=comentarios, calificacion_promedio=calificacion_promedio)

# Ruta para calificar película
@app.route('/pelicula/<int:pelicula_id>/calificar', methods=['POST'])
@login_required
def calificar_pelicula(pelicula_id):
    calificacion = int(request.form['calificacion'])

    # Verificar si el usuario ya calificó esta película
    calificacion_existente = client.table('calificaciones').select('*').eq('pelicula_id', pelicula_id).eq('usuario_id', current_user.id).execute().data
    
    if calificacion_existente:
        # Actualizar la calificación existente
        client.table('calificaciones').update({'calificacion': calificacion}).eq('id', calificacion_existente[0]['id']).execute()
    else:
        # Insertar nueva calificación
        client.table('calificaciones').insert({
            'calificacion': calificacion,
            'pelicula_id': pelicula_id,
            'usuario_id': current_user.id
        }).execute()

    flash("Calificación registrada correctamente.", "success")
    return redirect(url_for('ver_pelicula', pelicula_id=pelicula_id))

# Ruta para eliminar película
@app.route('/pelicula/<int:pelicula_id>/eliminar', methods=['POST'])
@login_required
def eliminar_pelicula(pelicula_id):
    # Solo el moderador puede eliminar la película
    pelicula = client.table('peliculas').select('*').eq('id', pelicula_id).execute().data[0]
    if pelicula['moderador_id'] != current_user.id:
        flash("No tienes permiso para eliminar esta película.", "danger")
        return redirect(url_for('home'))

    client.table('peliculas').delete().eq('id', pelicula_id).execute()
    flash("Película eliminada exitosamente.", "success")
    return redirect(url_for('home'))

# Ruta para comentar en una película
@app.route('/pelicula/<int:pelicula_id>/comentar', methods=['POST'])
@login_required
def comentar(pelicula_id):
    comentario = request.form['comentario']
    
    # Insertar el comentario en la base de datos
    client.table('comentarios').insert({
        'comentario': comentario,
        'pelicula_id': pelicula_id,
        'usuario_id': current_user.id,
        'fecha': 'now()'
    }).execute()
    
    return redirect(url_for('ver_pelicula', pelicula_id=pelicula_id))

# Ruta para eliminar comentario
@app.route('/comentario/<int:comentario_id>/eliminar', methods=['POST'])
@login_required
def eliminar_comentario(comentario_id):
    comentario = client.table('comentarios').select('*').eq('id', comentario_id).execute().data[0]

    # Solo el usuario que hizo el comentario puede eliminarlo
    if comentario['usuario_id'] != current_user.id:
        flash("No tienes permiso para eliminar este comentario.", "danger")
        return redirect(url_for('home'))

    client.table('comentarios').delete().eq('id', comentario_id).execute()
    flash("Comentario eliminado exitosamente.", "success")
    return redirect(url_for('ver_pelicula', pelicula_id=comentario['pelicula_id']))

@app.route('/perfil')
@login_required
def perfil():
    # Lógica para obtener datos del usuario
    usuario = client.table('usuarios').select('email').eq('id', current_user.id).execute().data[0]
    peliculas_subidas = client.table('peliculas').select('*').eq('moderador_id', current_user.id).execute().data
    comentarios = client.table('comentarios').select('*').eq('usuario_id', current_user.id).execute().data

    return render_template('perfil.html', usuario=usuario, peliculas_subidas=peliculas_subidas, comentarios=comentarios)

@app.route('/buscar', methods=['GET', 'POST'])
def buscar():
    peliculas = []
    if request.method == 'POST':
        termino = request.form['termino']
        
        # Buscar películas por título
        peliculas = client.table('peliculas').select('*').ilike('titulo', f'%{termino}%').execute().data

    return render_template('buscar.html', peliculas=peliculas)

@app.route('/mejores_calificaciones')
def mejores_calificaciones():
    # Obtener películas con sus calificaciones promedio ordenadas de mayor a menor
    peliculas = client.rpc('obtener_peliculas_mejor_calificadas').execute().data
    return render_template('mejores_calificaciones.html', peliculas=peliculas)


# Ruta para cerrar sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión.", "success")
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
