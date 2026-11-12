import sqlite3

c = sqlite3.connect("data/rootlens.db")
print("telemetry:", c.execute("select count(*), min(collected_at), max(collected_at) from telemetry_samples").fetchall())
print("kaynaklar:", c.execute("select source, count(*) from telemetry_samples group by source").fetchall())
print("observations:", c.execute("select count(*), min(created_at), max(created_at) from observations").fetchall())
print("son run:", c.execute("select * from collection_runs order by id desc limit 1").fetchall())