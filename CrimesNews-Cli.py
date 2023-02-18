from Core import executar
from datetime import datetime, timedelta

# definir valores padrão para as datas
hoje = datetime.today()
data_fim_padrao = hoje.strftime('%d/%m/%Y')
data_inicio_padrao = (hoje - timedelta(days=14)).strftime('%d/%m/%Y')

# solicitar entradas ao usuário
data_inicio_str = input(f'Data de início [{data_inicio_padrao}]: ') or data_inicio_padrao
data_fim_str = input(f'Data de fim [{data_fim_padrao}]: ') or data_fim_padrao
noticias_maximo_retornado = int(input('Máximo retornado [10]: ') or '10')
data_inicio = datetime.strptime(data_inicio_str, '%d/%m/%Y').date()
data_fim = datetime.strptime(data_fim_str, '%d/%m/%Y').date()

df = executar(data_inicio, data_fim, noticias_maximo_retornado)
df.to_excel('crimes.xlsx', index=False)