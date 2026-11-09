def current_identity() -> str:
    # Esta versión no autentica las peticiones: todas se atribuyen a una identidad
    # ficticia del laboratorio. Por eso la API solo se publica en 127.0.0.1.
    return 'empresa-a'
