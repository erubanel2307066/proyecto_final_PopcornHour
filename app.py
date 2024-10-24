from flask import Flask, render_template, request, redirect, url_for
import supabase

app = Flask(__name__)

# Configuración de Supabase
supabase_url = "https://druqkagvgwrsordpmgnb.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRydXFrYWd2Z3dyc29yZHBtZ25iIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mjk2NDIzOTgsImV4cCI6MjA0NTIxODM5OH0.RVH4k-D5C2iIdcfxISQZq6lnGRDBBeoAQDvhFoWjuvc"
client = supabase.create_client(supabase_url, supabase_key)

# Ruta para la página de inicio
@app.route('/')
def home():
    peliculas = client.table('peliculas').select('*').execute().data
    return render_template('home.html', peliculas=peliculas)

# Ruta para ver los detalles de una película
@app.route('/pelicula/<int:pelicula_id>')
def movie_details(pelicula_id):
    pelicula = client.table('peliculas').select('*').eq('id', pelicula_id).execute().data[0]
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
