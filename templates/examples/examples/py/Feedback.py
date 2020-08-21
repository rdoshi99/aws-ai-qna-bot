import json
import string
import boto3
import os
import collections
from collections import defaultdict
import botocore.response as br
import datetime

def handler(event, context):

    print(json.dumps(event))
    # event["res"]["session"]["previous"]["feedback"] = True

    kendraIndexId = None
    kendraQueryId = None
    kendraResultId = None
    kendraResponsibleQid = None

    if event.get('req',{}).get('session',{}).get('qnabotcontext',{}).get('kendra'):
        kendraIndexId = event.get('req').get('session').get('qnabotcontext').get('kendra').get('kendraIndexId')
        kendraQueryId = event.get('req').get('session').get('qnabotcontext').get('kendra').get('kendraQueryId')
        kendraResultId = event.get('req').get('session').get('qnabotcontext').get('kendra').get('kendraResultId')
        kendraResponsibleQid = event.get('req').get('session').get('qnabotcontext').get('kendra').get('kendraResponsibleQid')
    else:
        print("no kendra information present in session attribute qnabotcontext")

    try:
        #get the Question ID (qid) of the previous document that was returned to the web client 
        previous = event["req"]["session"]["qnabotcontext"]["previous"]
        previousQid = previous["qid"]
        previousQuestion = previous["q"]
        previousAnswer = previous["a"]
        previousAlt = previous["alt"]
        feedbackArg = event["res"]["result"]["args"][0]
        print(feedbackArg)
        
        # - Check feedbackArg from the UI payload. Parse for "thumbs_down_arg" feedback. Based on user action, sendFeedback through SNS, and log in Firehose. 
        if feedbackArg == "incorrect":
            sendFeedbackNotification(previousQid, previousAnswer, previousQuestion, previousAlt, feedbackArg)
            if (kendraIndexId is not None) and (kendraResponsibleQid==previousQid or kendraResponsibleQid=='KendraFAQ'):
                print("submitting NOT_RELEVANT to Kendra Feedback")
                submitFeedbackForKendra(kendraIndexId, kendraQueryId, kendraResultId, "NOT_RELEVANT")
            logFeedback(previousQid,previousAnswer,previousQuestion, previousAlt, feedbackArg)
            print("Negative feedback logged, and SNS notification sent")
        
        else:
            if (kendraIndexId is not None) and (kendraResponsibleQid==previousQid or kendraResponsibleQid=='KendraFAQ'):
                print("submitting RELEVANT to Kendra Feedback")
                submitFeedbackForKendra(kendraIndexId, kendraQueryId, kendraResultId, "RELEVANT")
            logFeedback(previousQid, previousAnswer, previousQuestion, previousAlt, feedbackArg)
            print("Positive feedback logged")
    except Exception as e:
        print("Exception caught (no previous question?): ", e)
        print("Feedback not logged.")
    return event

#logs feedback for the questions
def logFeedback(qid,answer,question, alt, inputText):
    jsonData = {"qid":"{0}".format(qid),
        "utterance":"{0}".format(question),
        "answer":"{0}".format(answer),
        "alternate":"{0}".format(alt),
        "feedback":"{0}".format(inputText),
        "datetime":"{0}".format(datetime.datetime.now().isoformat())
    }
    jsondump=json.dumps(jsonData,ensure_ascii=False)
    client = boto3.client('firehose')
    response = client.put_record(
        DeliveryStreamName=os.environ['FIREHOSE_NAME'],
        Record={
            'Data': jsondump
        }
    )
    #uncomment below if you would like to see the response returned by the firehose stream
    #print(response)

# - Sends SNS notification for feedback.
def sendFeedbackNotification( qid,answer,question, alt, inputText):
    
    notificationBody = "\n\nTimestamp: {5} Question ID: {0}\nQuestion: {1} \nAnswer: {2} \nAlternative Answer: {3} \nFeedback: {4}".format(qid,question,answer, alt, inputText, datetime.datetime.now().isoformat())
   
    #print(notificationBody)
    message = {"qnabot": "publish to feedback topic"}
    client = boto3.client('sns')
    response = client.publish(
        TargetArn=  os.environ['SNS_TOPIC_ARN'], 
        Message=json.dumps({'default': notificationBody
        }),
        Subject='QnABot - Feedback received',
        MessageStructure='json'
    )


# - Sends feedback notification for Kendra feedback.
def submitFeedbackForKendra(kendraIndexId, kendraQueryId, kendraResultId, kendraRelevancy):

    client = boto3.client('kendra')
    response = client.submit_feedback(
        IndexId=kendraIndexId,
        QueryId=kendraQueryId,
        RelevanceFeedbackItems=[
            {
                'ResultId': kendraResultId,
                'RelevanceValue': kendraRelevancy
            },
        ]
    )
    print("Feedback submitted to Kendra")
