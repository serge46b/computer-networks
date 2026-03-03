from time import sleep

from ping3 import ping


HOSTLIST = [
    "www.google.com",
    "ya.ru",
    "mtiyt.ru",
    "www.youtube.com",
    "vk.com",
    "nonexistingdomain.wtf",
    "nsu.ru",
    "www.telegram.org",
    "discord.com",
    "pornhub.com",
]
PING_TIMES = 10
SLEEP_TIMEOUT = 0.1

f = open("./01 ping/out.csv", "w")
f.write("Host, min time, avg time, max time, lost percentage, ping count\n")

for host in HOSTLIST:
    mn_time = None
    mx_time = None
    avg_time = None
    lost_count = 0
    print(f"{'-'*7}Pinging '{host}'{'-'*7}")
    for _ in range(PING_TIMES):
        time = ping(host)
        # print(f"Host: {host} | Ping time: {time:.4f}s")
        sleep(SLEEP_TIMEOUT)
        if time == False or time is None:
            lost_count += 1
            continue
        if mn_time is None or mn_time > time:
            mn_time = time
        if mx_time is None or mx_time < time:
            mx_time = time
        if avg_time is None:
            avg_time = 0
        avg_time += time
    if avg_time is not None and lost_count < PING_TIMES:
        avg_time /= PING_TIMES
    f.write(
        f"{host}, {mn_time}, {avg_time}, {mx_time}, {lost_count / PING_TIMES * 100}, {PING_TIMES}\n"
    )
    print(f"Host: {host}")
    print(f"Min time: {mn_time}")
    print(f"Max time: {mx_time}")
    print(f"Avg time: {avg_time}")
    print(f"Lost count: {lost_count}")
    print(f"Lost percentage: {lost_count / PING_TIMES * 100}%")
    print(f"Ping times: {PING_TIMES}")
