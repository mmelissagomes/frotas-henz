from django.shortcuts import render, redirect

# ✅ Lista de usuários permitidos
USUARIOS_ACEITOS = {
    "melissa.admin": "FrotaControle#admin",
    "Silvia.admin": "Mw!6DNUefKbMdxF"
}

# ✅ Página de login acessada via "/"
def login_view(request):
    if request.method == "POST":
        usuario = request.POST.get("usuario")
        senha = request.POST.get("senha")

        if usuario in USUARIOS_ACEITOS and USUARIOS_ACEITOS[usuario] == senha:
            return redirect("home")  # vai para /home

        return render(request, "login.html", {"erro": "Usuário ou senha inválidos."})

    return render(request, "login.html")  # GET inicial

# ✅ Página exibida após login bem-sucedido
def home_view(request):
    return render(request, "home.html")
