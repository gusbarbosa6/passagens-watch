NAMES = {
    "SAO": "São Paulo", "GRU": "Guarulhos", "CGH": "Congonhas", "VCP": "Viracopos (Campinas)",
    "RIO": "Rio de Janeiro", "GIG": "Galeão (RJ)", "SDU": "Santos Dumont (RJ)", "BSB": "Brasília",
    "CNF": "Belo Horizonte", "BHZ": "Belo Horizonte", "SSA": "Salvador", "REC": "Recife",
    "FOR": "Fortaleza", "NAT": "Natal", "MCZ": "Maceió", "AJU": "Aracaju", "JPA": "João Pessoa",
    "SLZ": "São Luís", "THE": "Teresina", "BEL": "Belém", "MAO": "Manaus", "FLN": "Florianópolis",
    "POA": "Porto Alegre", "CWB": "Curitiba", "IGU": "Foz do Iguaçu", "GYN": "Goiânia",
    "CGB": "Cuiabá", "VIX": "Vitória", "PMW": "Palmas", "NVT": "Navegantes", "JDO": "Juazeiro do Norte",
    "FEN": "Fernando de Noronha", "BPS": "Porto Seguro", "IOS": "Ilhéus", "MII": "Marília",
    "LIS": "Lisboa", "OPO": "Porto", "MAD": "Madri", "BCN": "Barcelona", "PAR": "Paris",
    "LON": "Londres", "ROM": "Roma", "MIL": "Milão", "AMS": "Amsterdã", "FRA": "Frankfurt",
    "MUC": "Munique", "ZRH": "Zurique", "IST": "Istambul", "DXB": "Dubai", "DOH": "Doha",
    "NYC": "Nova York", "MIA": "Miami", "MCO": "Orlando", "LAX": "Los Angeles", "SFO": "São Francisco",
    "YTO": "Toronto", "MEX": "Cidade do México", "CUN": "Cancún", "PTY": "Cidade do Panamá",
    "BOG": "Bogotá", "LIM": "Lima", "SCL": "Santiago", "EZE": "Buenos Aires", "BUE": "Buenos Aires",
    "MVD": "Montevidéu", "ASU": "Assunção", "CUZ": "Cusco", "UIO": "Quito", "PUJ": "Punta Cana",
    "HAV": "Havana", "JNB": "Joanesburgo", "CPT": "Cidade do Cabo", "TYO": "Tóquio", "SEL": "Seul",
    "BKK": "Bangkok", "SIN": "Singapura", "SYD": "Sydney", "AKL": "Auckland", "PEK": "Pequim",
}


def name(code: str) -> str:
    n = NAMES.get(code)
    return f"{n} ({code})" if n else code
