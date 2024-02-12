class CamadaEnlace:
    ignore_checksum = False

    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}. O ip_outra_ponta é o IP do
        host ou roteador que se encontra na outra ponta do enlace, escrito como
        uma string no formato 'x.y.z.w'. A linha_serial é um objeto da classe
        PTY (vide camadafisica.py) ou de outra classe que implemente os métodos
        registrar_recebedor e enviar.
        """
        self.enlaces = {}
        self.callback = None
        # Constrói um Enlace para cada linha serial
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self._callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar em qual enlace se encontra o next_hop.
        """
        # Encontra o Enlace capaz de alcançar next_hop e envia por ele
        self.enlaces[next_hop].enviar(datagrama)

    def _callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


class Enlace:
    def __init__(self, linha_serial):
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)
        self.buffer_recebimento = bytearray()
        self.escapando = False

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        # Bytes especiais e suas sequências de escape
        DELIMITADOR = 0xC0
        ESCAPE = 0xDB
        DELIMITADOR_ESCAPADO = b'\xDB\xDC'
        ESCAPE_ESCAPADO = b'\xDB\xDD'

        # Inicia com o delimitador
        quadro = bytes([DELIMITADOR])

        for byte in datagrama:
            if byte == DELIMITADOR:
                # Substitui o delimitador por sua sequência de escape
                quadro += DELIMITADOR_ESCAPADO
            elif byte == ESCAPE:
                # Substitui o byte de escape por sua sequência de escape
                quadro += ESCAPE_ESCAPADO
            else:
                # Adiciona o byte ao quadro sem modificação
                quadro += bytes([byte])

        # Finaliza com o delimitador
        quadro += bytes([DELIMITADOR])

        # Envia o quadro pela linha serial
        self.linha_serial.enviar(quadro)

    def __raw_recv(self, dados):
        # Constantes para os bytes especiais
        DELIMITADOR = 0xC0
        ESCAPE = 0xDB
        ESCAPE_PARA_C0 = 0xDC
        ESCAPE_PARA_DB = 0xDD

        for byte in dados:
            if self.escapando:
                if byte == ESCAPE_PARA_C0:
                    self.buffer_recebimento.append(DELIMITADOR)
                elif byte == ESCAPE_PARA_DB:
                    self.buffer_recebimento.append(ESCAPE)
                self.escapando = False
            elif byte == ESCAPE:
                self.escapando = True
            elif byte == DELIMITADOR:
                if len(self.buffer_recebimento) > 0:
                    try:
                        # Tenta chamar o callback com o datagrama completo
                        self.callback(bytes(self.buffer_recebimento))
                    except Exception:
                        # Ignora a exceção, mas mostra na tela
                        import traceback
                        traceback.print_exc()
                    finally:
                        # Limpa o buffer independentemente de sucesso ou falha
                        self.buffer_recebimento.clear()
            else:
                self.buffer_recebimento.append(byte)
