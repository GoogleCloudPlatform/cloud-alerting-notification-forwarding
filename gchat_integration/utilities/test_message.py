import json

f = open('/home/binglin/oss-test-1/oss/oss-gchat-handler/gchat_integration/utilities/example_message.json')
data = json.load(f)
incident_display_name = data['incident']['condition']['displayName']
incident_condition_threshold = data['incident']['condition']['conditionThreshold']
incident_resource_labels = data['incident']['resource']['labels']

print(incident_display_name)
print(incident_condition_threshold)
print(incident_resource_labels)