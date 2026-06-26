import requests

class NFSeService:

    def __init__(self):
        self.api_url = "URL_DA_PREFEITURA"
        self.token = "SEU_TOKEN"

    def emitir_nfse(self, user, cliente, servico):
        payload = {
            "prestador": {
                "cnpj": user.cnpj,
                "inscricao_municipal": user.inscricao
            },
            "tomador": {
                "nome": cliente.nome,
                "cpf": cliente.cpf,
                "endereco": cliente.endereco
            },
            "servico": {
                "descricao": servico.descricao,
                "valor": servico.valor
            }
        }

        return requests.post(self.api_url + "/nfse", json=payload)
