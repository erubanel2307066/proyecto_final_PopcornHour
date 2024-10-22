from flask import Flask, render_template, request, redirect, url_for
import supabase

app = Flask(__name__)

# Configuración de Supabase
supabase_url = "TU_SUPABASE_URL"
supabase_key = "TU_SUPABASE_KEY"
client = supabase.create_client(supabase_url, supabase_key)

# Ruta para la página de inicio
@app.route('/')
def home():
    peliculas = client.table('Peliculas').select('*').execute().data
    return render_template('home.html', peliculas=peliculas)

# Ruta para ver los detalles de una película
@app.route('/pelicula/<int:pelicula_id>')
def movie_details(pelicula_id):
    pelicula = client.table('Peliculas').select('*').eq('id', pelicula_id).execute().data[0]
    comentarios = client.table('Comentarios').select('*').eq('pelicula_id', pelicula_id).execute().data
    return render_template('movie_details.html', pelicula=pelicula, comentarios=comentarios)

# Ruta para añadir comentarios (sólo usuarios estándar)
@app.route('/pelicula/<int:pelicula_id>/comentar', methods=['POST'])
def comentar(pelicula_id):
    comentario = request.form.get('comentario')
    user_id = request.form.get('user_id')
    client.table('Comentarios').insert({'pelicula_id': pelicula_id, 'user_id': user_id, 'texto': comentario}).execute()
    return redirect(url_for('movie_details', pelicula_id=pelicula_id))

if __name__ == "__main__":
    app.run(debug=True)
