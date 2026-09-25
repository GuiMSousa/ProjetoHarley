// Bloqueado no saneamento pré-Change 6: fluxo de recuperação por magic link não homologado.
// O endpoint público permanecia exposto sem uso pela aplicação. Reativar somente por Change aprovada.
query "reset/magic-link-login" verb=POST {
  api_group = "Authentication"

  input {
  }

  stack {
    precondition (false) {
      error_type = "accessdenied"
      error = "Recuperação de acesso indisponível. Procure o gerente responsável."
    }
  }

  response = null
  tags = ["xano:quick-start"]
  guid = "fSrBbThgAOO916a7nk0aMtLz5HE"
}
