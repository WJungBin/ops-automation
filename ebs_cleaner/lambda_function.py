import json
import boto3
import logging
import json
import requests
from datetime import datetime, timezone, timedelta


logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

class EBSCleaner:
    def __init__(self, region):
        self.region = region
        self.ec2 = boto3.client("ec2", region_name=self.region)
        self.webhook_url = "Webhook URL"

    def getEBSAvailable(self):
        volumes = self.ec2.describe_volumes()["Volumes"]
        return [
            {
                "VolumeId": v["VolumeId"],
                "State": v["State"],
                "Size": v["Size"],
                "CreateTime": str(v["CreateTime"]),  # 수동 변환
                "Name": next((tag["Value"] for tag in v.get("Tags", []) if tag["Key"] == "Name"), None)
            }
            for v in volumes
            if v["State"] == "available"
            and (datetime.now(timezone.utc) - v["CreateTime"]) >= timedelta(days=3)
            and not any(tag["Key"] == "Keep" and tag["Value"].lower() == "true" for tag in v.get("Tags", []))
            and not v.get("SnapshotId")
        ]
        
    def getAvailableVolumeIds(self):
        volumes = self.getEBSAvailable()
        if not volumes:
            logger.info("Volume all Used")
        return [v["VolumeId"] for v in volumes]
        
    def ebsDeleteWarningHook(self, volume_ids):
        header = {
            'Content-Type': 'application/json'
        }
        data = {
            'body' : '3일 이상 미사용 되고 있는 EBS 리스트입니다.',
            'connectColor' : '#FAC11B',
            'connectInfo' : [
                {
                    'title' : '14일 이상 미사용 지속 시 삭제 예정입니다. \n삭제하면 안되는 EBS의 경우 Keep :  true 태그를 추가하세요.\n',
                    'description' : (
                        f"\nEBS ID: {volume_ids}\n"
                    )
                }
            ] 
        }
        response_webhook = requests.post(self.webhook_url, headers = header ,json=data)
        logger.debug("Warning Webhook Post")
        return response_webhook

    def deleteEBSAvailable(self):
        volumes = self.ec2.describe_volumes()["Volumes"]
        return [
            {
                "VolumeId": i["VolumeId"],
                "State": i["State"],
                "Size": i["Size"],
                "CreateTime": str(i["CreateTime"]),  # 수동 변환
                "Name": next((tag["Value"] for tag in i.get("Tags", []) if tag["Key"] == "Name"), None)
            }
            for i in volumes
            if i["State"] == "available"
            and (datetime.now(timezone.utc) - i["CreateTime"]) >= timedelta(days=14)
            and not any(tag["Key"] == "Keep" and tag["Value"].lower() == "true" for tag in i.get("Tags", []))
            and not i.get("SnapshotId")
        ]

    def getDeleteVolumeIds(self):
        volumes = self.deleteEBSAvailable()
        deleted_ids = []

        for i in volumes:
            try:
                self.ec2.delete_volume(VolumeId=i["VolumeId"])
                logger.info(f"Deleted volume {i['VolumeId']}")
                deleted_ids.append(i["VolumeId"])
            except Exception as e:
                logger.error(f"Failed to delete volume {i['VolumeId']}: {e}")

        return deleted_ids
    
    
    def ebsDeleteHook(self, delete_volume_ids):
        header = {
            'Content-Type': 'application/json'
        }
        data = {
            'body' : '14일 이상 미사용 EBS가 삭제 되었습니다.',
            'connectColor' : '#FAC11B',
            'connectInfo' : [
                {
                    'title' : f'{delete_volume_ids}'
                }
            ] 
        }
        response_webhook = requests.post(self.webhook_url, headers = header ,json=data)
        logger.debug("Delete Webhook Post")
        return response_webhook




def lambda_handler(event, context):
    region = "Region"
    ebs = EBSCleaner(region)
    
    volume_ids = ebs.getAvailableVolumeIds()
    if volume_ids:
        ebs.ebsDeleteWarningHook(volume_ids)

    delete_volume_ids = ebs.getDeleteVolumeIds()
    if delete_volume_ids:
        ebs.ebsDeleteHook(delete_volume_ids)