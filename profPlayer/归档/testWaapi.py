import waapi

client = waapi.WaapiClient()

result = client.call("ak.wwise.core.getProjectInfo")
print(result)
print("连接成功，没有问题")

client.disconnect()


input("Press Enter to exit...")


