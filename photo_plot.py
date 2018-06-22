import pandas as pd
import matplotlib.pyplot as plt

def photopng():
    data = pd.DataFrame(pd.read_csv("data/trade.csv"))
    data.dropna()
    data = [["price","ctime"]]
    plt.scatter(data["price"],data["ctime"])
    plt.xlim()
