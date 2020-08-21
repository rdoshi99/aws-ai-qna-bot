var properties={
    
    "ElasticsearchClusterConfig": {
       "DedicatedMasterEnabled": false,
       "InstanceCount": 2,
       "InstanceType": {"Fn::If": [ "Encrypted", "c5.large.elasticsearch", "t2.small.elasticsearch"]},
       "ZoneAwarenessEnabled": "true"
    },
    "EBSOptions": {
       "EBSEnabled": true,
       "VolumeSize": 10,
       "VolumeType": "gp2"
    },
    "ElasticsearchVersion": "7.7",
    "SnapshotOptions": {
       "AutomatedSnapshotStartHour": "0"
    },
    "AdvancedOptions": {
       "rest.action.multi.allow_explicit_index": "true"
    },
    "EncryptionAtRestOptions": {
       "Enabled": {"Fn::If": [ "Encrypted", true, false]}
    }
}

module.exports={
    "ElasticsearchDomain": {
        "Type": "AWS::Elasticsearch::Domain",
        "DependsOn":["PreUpgradeExport"],
        "Condition":"CreateDomain",
        "Properties":properties 
    },
    "ElasticsearchDomainUpdate": {
         "Type": "Custom::ElasticSearchUpdate",
         "DependsOn":["CognitoDomain"],
         "Properties":{
            "ServiceToken": { "Fn::GetAtt" : ["CFNLambda", "Arn"] },
            "DomainName":{"Fn::GetAtt":["ESVar","ESDomain"]},
            "CognitoOptions":{
                Enabled: true ,
                IdentityPoolId: {"Ref":"KibanaIdPool"},
                RoleArn:{"Fn::GetAtt":["ESCognitoRole","Arn"]},
                UserPoolId: {"Ref":"UserPool"}
            },
            "AccessPolicies": {"Fn::Sub":JSON.stringify({
               "Version": "2012-10-17",
               "Statement": [
                  {
                     "Sid": "CognitoAuth",
                     "Principal": {
                        "AWS":"${KibanaRole.Arn}"
                     },
                     "Effect": "Allow",
                     "Action": "es:ESHttp*",
                     "Resource":"${ESVar.ESArn}/*"
                  }
               ]
            })},
        }
    },
    "ESCognitoRole": {
      "Type": "AWS::IAM::Role",
      "Properties": {
        "AssumeRolePolicyDocument": {
          "Version": "2012-10-17",
          "Statement": [
            {
				"Effect": "Allow",
				"Principal": {
                    "Service": "es.amazonaws.com"
				},
                "Action": "sts:AssumeRole"
            }
          ]
        },
        "Path": "/",
        "ManagedPolicyArns": ["arn:aws:iam::aws:policy/AmazonESCognitoAccess"],
      }
    }
}
