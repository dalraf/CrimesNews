from tkinter import *
from datetime import datetime
from datetime import timedelta
from Core import executar
from datetime import datetime, timedelta

def main(data_inicio_str, data_fim_str, noticias_maximo_retornado):
    data_inicio = datetime.strptime(data_inicio_str, '%d/%m/%Y').date()
    data_fim = datetime.strptime(data_fim_str, '%d/%m/%Y').date()
    df = executar(data_inicio, data_fim, noticias_maximo_retornado)
    df.to_excel('crimes.xlsx', index=False)

root = Tk()
root.title("Crime News")

# Define as datas de hoje como padrão
hoje = datetime.today()
data_fim_padrao = hoje.strftime('%d/%m/%Y')
data_inicio_padrao = (hoje - timedelta(days=14)).strftime('%d/%m/%Y')

# Cria o campo de entrada para a data de início
label_inicio = Label(root, text="Data Início:")
label_inicio.grid(row=0, column=0, padx=10, pady=10)
data_inicio = Entry(root, width=10)
data_inicio.insert(0, data_inicio_padrao)
data_inicio.grid(row=0, column=1, padx=10, pady=10)

# Cria o campo de entrada para a data de fim
label_fim = Label(root, text="Data Fim:")
label_fim.grid(row=1, column=0, padx=10, pady=10)
data_fim = Entry(root, width=10)
data_fim.insert(0, data_fim_padrao)
data_fim.grid(row=1, column=1, padx=10, pady=10)

# Cria o campo de entrada para o valor noticias_maximo_retornado
label_noticias_maximo_retornado = Label(root, text="Notícias maximo retornado:")
label_noticias_maximo_retornado.grid(row=2, column=0, padx=10, pady=10)
noticias_maximo_retornado = Entry(root, width=10)
noticias_maximo_retornado.insert(0, "10")
noticias_maximo_retornado.grid(row=2, column=1, padx=10, pady=10)

# Cria o botão de execução
botao_executar = Button(root, text="Executar", command=lambda: main(data_inicio.get(), data_fim.get(), int(noticias_maximo_retornado.get())))
botao_executar.grid(row=3, column=1, padx=10, pady=10)

root.mainloop()
