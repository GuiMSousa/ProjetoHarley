// Update FAQ record
query "faq/{faq_id}" verb=PUT {
  api_group = "Crud"

  input {
    int faq_id? filters=min:1
    dblink {
      table = "FAQ"
    }
  }

  stack {
    db.edit FAQ {
      field_name = "id"
      field_value = $input.faq_id
      enforce_hidden_fields = false
      data = {pergunta: $input.pergunta, resposta: $input.resposta}
    } as $model
  }

  response = $model
  guid = "BP6HirOmrKs-dnNOiHio4PbcMEY"
}