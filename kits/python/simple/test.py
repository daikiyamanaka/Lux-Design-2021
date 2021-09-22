from kaggle_environments import make
#from simple.my_agent import agent
from my_agent import agent



env = make("lux_ai_2021", configuration={"seed": 562124210, "loglevel": 2, "annotations": True}, debug=True)

steps = env.run([agent, "simple_agent"])

#env.render(mode="ipython", width=1200, height=800)
html = env.render(mode="html")

out = open("out.html", 'w')
out.write(html)
out.close()
