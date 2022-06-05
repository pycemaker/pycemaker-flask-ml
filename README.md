# CRISP-DM

### BUSINESS UNDERSTADING

O cliente necessita de uma solução que informe a saúde do sistema e o tempo restante até uma possível falha. Para essa necessidade será desenvolvido um sistema de ML que irá pontuar a saúde do sistema e prever a próxima falha.

### DATA UNDERSTANDING

A aplicação Pycemaker Form Server está sendo observada pela aplicação Pycemaker Prometheus que atualiza a cada 5 segundos todas as métricas associadas ao consumo de rede e hardware.  

Alguns métricas relevantes da aplicação Pycemaker Prometheus:  

 - **system_cpu_usage:** valor atual de processamento do sistema
 - **process_cpu_usage:** valor atual de processamento da aplicação
 - **disk_free_bytes:** valor atual de espaço livre no disco
 - **disk_total_bytes:** valor atual do espaço total do disco
 - **jvm_memory_used_bytes:** dicionário detalhado de uso de memória atual
 - **jvm_memory_max_bytes:** dicionário detalhado de uso máximo de memória atual
 - **http_server_requests_seconds_count:** dicionário detalhado de contagem total de requisições
 - **http_server_requests_seconds_sum:** dicionário detalhado de contagem total dos tempos de resposta das requisições
 - **hikaricp_connections_active:** número de conexões ativas do sistema com o banco de dados

### DATA PREPARATION

Para que o ML seja desenvolvido será necessário coletar as métricas do Prometheus. Adotou-se como configuração para esse projeto, coletar a cada 5 segundos alguns desses dados e salvá-los em um banco NoSQL (MongoDB), onde cada collection será a métrica de um recurso observado. Para isso utilizou-se a aplicação NiFi que coleta e salva as métricas de recursos em collections separadas. Além disso, para que faça sentido analisar uma série temporal, desenvolveu-se uma aplicação em Python com a biblioteca Locust que acessa continuadamente a aplicação Pycemaker Form Server com um padrão de execução, ou seja, a cada uma hora a aplicação emula a concorrência escalar de 10 a 1000 usuários e de 1000 a 10 usuários, formando uma curva que se repete ao longo do tempo. Abaixo detalha-se os dados coletados e as respectivas collections.  

Recursos que foram coletadas:  
 - **Uso de CPU (cpu_usage):** process_cpu_usage
 - **Uso de RAM (jvm_memory_usage):** jvm_memory_used_bytes / jvm_memory_max_bytes (a função sum do Prometheus fará a soma de todos os dicionários da métrica)
 - **Número de Requisições (request_count):** http_server_requests_seconds_count (a função irate do Prometheus fará o cálculo para o período de 5 segundos, duas coletas são feitas o valor de requisições bem-sucedidas e de requisições que falharam)
 - **Tempo de Resposta (response_time):** http_server_requests_seconds_sum / http_server_requests_seconds_count (a função irate do Prometheus fará o cálculo médio para o período de 5 segundos)

Recursos que não foram coletados:  
 - **Uso de CPU do Sistema:** o valor de processamento do sistema não se trata da aplicação em análise, mas do sistema em que a aplicação está executando, portanto, trata-se do valor de uso de todos as aplicações utilizadas naquele sistema
 - **Uso de Disco:** o sistema não apresenta crescimento de disco nos testes aplicados pois o sistema é iniciado com tamanho fixo de dados no banco e o teste irá salvar novos registros e exclui-los em seguida
 - **Número de Conexões com o Banco de Dados:** observou-se que o valor de conexões não foi alterado durante os testes preliminares

Estrutura de cada collection:  

```javascript
cpu_usage: {
  consume_percent: string do valor convertido em porcentagem
  time_series: datetime da coleta
  criticity: classificação do valor em low, medium, high ou critical (< 25%, < 50%, < 75% ou < 100%)
  value: valor na escala 0 a 1
}
```

```javascript
jvm_memory_usage: {
  consume_percent: string do valor convertido em porcentagem
  time_series: datetime da coleta
  criticity: classificação do valor em low, medium, high ou critical (< 25%, < 50%, < 75% ou < 100%)
  value: valor na escala 0 a 1
}
```

```javascript
request_count: {
  time_series: datetime da coleta
  criticity: classificação do valor total (value_success + value_fail) em low, medium, high ou critical (< 15, < 30, < 60 ou > 61)
  value_success: valor inteiro ou decimal
  value_fail: valor inteiro ou decimal
}
```

```javascript
response_time: {
  consume_percent: string do valor convertido em porcentagem
  time_series: datetime da coleta
  criticity: classificação do valor em regular ou critical (< 0.3 ou > 0.3)
  value: valor na escala 0 a 1
}
```

### MODELING & EVALUATION

O documento *.ipynb descreve a modelagem do ML e sua avaliação.

### DEPLOYMENT

A implantação do ML será feita em aplicação Python com Flask como microserviço, o agendador de tarefas APScheduler fará o treinamento do ML a cada 3 horas e as seguintes rotas estarão disponíveis:  
1. Rota que devolve os dados de saúde para um intervalo solicitado
2. Rota que devolve os dados de previsão para um intervalo solicitado
3. Rota que devolve o dado atual de saúde do sistema, o dado de previsão de saúde do sistema para o tempo atual e o tempo restante até o próximo evento de falha