import json
import boto3
import logging
import os
import requests
import datetime
import time
from datetime import timezone # AMI 삭제 시 시간 데이터값을 추출하기 위한 모듈
from concurrent.futures import ThreadPoolExecutor, as_completed # AMI 생성 확인을 할 때 병렬로 처리하기 위한 모듈

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


# AMI 생성 class
class management_image_in_deploy():
    def __init__(self, instance_name_list, create_webhook_url, delete_webhook_url, ami_name):
        self.instance_name = instance_name_list # 인스턴스 이름을 받아 저장
        self.instance_ids = [] # 인스턴스 id 를 담을 빈 리스트 생성
        self.instance_name_filtered = []
        self.create_webhook_url = create_webhook_url
        self.delete_webhook_url = delete_webhook_url
        self.ami_ids = []
        self.ami_name = ami_name
        self.ami_names = []

        
    def get_instance_id(self):
        client = boto3.client('ec2')
        for name in self.instance_name: # for문 시작
            # instance_name 값을  기반으로 인스턴스 조회
            response = client.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:Name',
                        'Values': [name] # Name 태그 기반
                    },
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running'] # running 인스턴스만 조회
                    }
                ]
            )
            all_instances = [] # 인스턴스 이름을 담을 빈 리스트 생성
            for res in response['Reservations']:
                all_instances.extend(res['Instances'])
            
            # 인스턴스 ID 출력
            instance_ids_in_all = [i['InstanceId'] for i in all_instances]
            logger.debug(f"Found instance IDs for {name}: {instance_ids_in_all}")

            # 실행중인 인스턴스가 없을 경우 웹훅 발송 후 다음 인스턴스 진행
            if not all_instances:
                logger.warning(f"No running instances found with Name tag: {name}")
                self.ami_notfound_webhook_post(name)
                continue

            # LaunchTime 기준으로 오름차순 정렬 후 가장 위에 인스턴스 선택 (즉, 켜진지 가장 오래된 인스턴스로 선택)
            sorted_instances = sorted(all_instances, key=lambda i: i['LaunchTime'], reverse=False)
            instance_id = sorted_instances[0]['InstanceId']
            logger.debug(f"Selected instance_id for {name}: {instance_id} (LaunchTime: {sorted_instances[0]['LaunchTime']})")

            self.instance_ids.append(instance_id)
            self.instance_name_filtered.append(name)


        logger.debug(f"instance_ids: {self.instance_ids}")
        return self.instance_ids # return 으로 instance_ids 를 반환시켜 값을 저장 (안하면 none으로 되어 에러 발생) 
        # 즉, get_instance_id 자체의 결과 자체가 instance_ids 로 반환됨
        
        
            
    # create_image() API는 BlockDeviceMappings를 생략하면, 기존 인스턴스의 EBS 설정을 그대로 사용
    def create_image(self): # class 자신의 변수 및 함수를 호출하기위해 self 로 호출
        
        # 시간 세팅 (class 안에 넣어야 클래스가 호출 될 때마다 시간이 갱신됨)
        now = datetime.datetime.now()
        nowDatetime = now.strftime('%Y-%m-%d_%H_%M')

        client = boto3.client('ec2')
        sfn = boto3.client('stepfunctions')
        instance_ids = self.get_instance_id()  # 리스트 형태의 instance_ids 변수를 끌고옴 (위에 return 으로 클래스 반환값 자체가 인스턴스 id의 배열이기 때문)
        '''
        위 get_instance_id 클래스의 리턴값인 instance_ids 리스트와, instance_name 의 리스트가 같은 순서로 같이 배열이 돌아야함.
        즉 create_image 할 때 두 리스트가 동일한 인덱스 넘버를 가지고 for문을 돌아야함.
        len(instance_ids) 는 리스트의 인덱스 넘버를 받음. (예: 3개 인스턴스면 3)
        range는 인덱스 넘버를 생성시킴. (예: len(instance_ids)가 3이면 0, 1, 2 이런식으로)
        결론적으로 ids 는 생성 요청한 인스턴스 갯수와 동일한 횟수만큼 반복해서 돌게됨.
        '''
        
        for ids in range(len(instance_ids)):
            # instance_ids와 instance_name 리스트에서 같은 인덱스를 사용해 1:1 매핑된 값 추출
            instance_id = instance_ids[ids]
            instance_name = self.instance_name_filtered[ids]
            self.ami_name = f"{instance_name}-Deploy-{nowDatetime}" # ami name을 지역변수화 하여 활용
            # AMI 생성 API
            response = client.create_image(
                Description='Created by Lambda',
                InstanceId=instance_id,
                Name=f'{instance_name}-Deploy-{nowDatetime}',
                NoReboot=True, # 생성 시 재부팅 안함
                TagSpecifications=[
                    {
                        'ResourceType': 'image',
                        'Tags': [
                            {'Key': 'Name', 'Value': f'{self.ami_name}'}, # 인스턴스 네임을+Deploy 태그를 Name 태그에 삽입
                            {'Key': 'Reason', 'Value': 'Deploy'}
                        ]
                    },
                ]
            )
            self.ami_ids.append(response['ImageId']) # 아래 AMI 상태체크에 활용하기 위해 생성요청이 들어간 ami id를 추출해서 리스트에 담음
            self.ami_names.append(self.ami_name) # 아래 AMI 상태체크 후 웹훅 발송에 활용하기 위해 ami name 을 리스트에 담음
        print(self.ami_ids)
        logger.debug(f"AMI 생성 완료: {self.ami_ids}")
        response = sfn.start_execution(
            stateMachineArn='AWS Step Functions ARN',
            input=json.dumps({
                'ami_ids': self.ami_ids
            })
        )        
        

    # AMI 생성 알림 웹훅 발송
    def ami_create_webhook_post(self):
        header = {
            'Content-Type': 'application/json'
        }
        data = {
            'body' : 'Start AMI Create',
            'connectColor' : '#28a745',
            'connectInfo' : [
                {
                    'title' : 'Create AMI For regular Deploy. Please check the list.',
                    'description' : f'{self.instance_name}'
                }
            ] 
        }
        response_webhook = requests.post(self.create_webhook_url, headers = header ,json=data)
        return response_webhook

    def ami_create_success_webhook_post(self, ami_name):
        header = {
            'Content-Type': 'application/json'
        }
        data = {
            'body' : 'Complete AMI Create.',
            'connectColor' : '#28a745',
            'connectInfo' : [ 
                {
                    'title' : 'Complete AMI Create. AMI State Available.',
                    'description' : f'{ami_name}'
                }
            ] 
        }
        response_webhook = requests.post(self.create_webhook_url, headers = header ,json=data)
        return response_webhook


    # AMI 삭제할 때 웹훅 발송
    def ami_delete_webhook_post(self, snapshot_id, image_id, name_tag):
        header = {
            'Content-Type': 'application/json'
        }
        data = {
            'body' : 'Delete AMI that is more than 2 weeks old',
            'connectColor' : '#FAC11B',
            'connectInfo' : [
                {
                    'title' : 'Delete AMI/Snapshot Last Time. Please check the list.',
                    'description' : (
                        f"Deleting Snapshot: {snapshot_id}\n"
                        f"AMI ID: {image_id}\n"
                        f"Name Tag: {name_tag}"
                    )
                }
            ] 
        }
        response_webhook = requests.post(self.delete_webhook_url, headers = header ,json=data)
        return response_webhook
    # AMI 생성 요청 서버가 존재하지 않을 경우 웹훅 발송
    def ami_notfound_webhook_post(self, name):
        header = {
            'Content-Type': 'application/json'
        }
        data = {
            'body' : 'Server Not Found',
            'connectColor' : '#FF0000',
            'connectInfo' : [
                {
                    'title' : f'Not Found Server : {name}',
                    'description' : f"Failed Create AMI {name}"
                }
            ] 
        }
        response_webhook = requests.post(self.create_webhook_url, headers = header ,json=data)
        return response_webhook


    # 오래된 AMI 및 Snapshot 삭제 API
    def old_image_delete(self):
        now = datetime.datetime.now()
        nowDatetime = now.strftime('%Y-%m-%d_%H_%M')
        days_old = 14 # 생성일 기준 이주일 후 만료로 지정
        expire_date = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=days_old)
        client = boto3.client('ec2')
        # images 라는 지역 변수 안에 describe image 한 결과값을 리스트 형태로 저장
        images = client.describe_images( 
            Filters=[
                {
                    'Name': 'tag:Reason',
                    'Values': ['Deploy']
                }
            ],
            Owners=['self']
        )
        #print(json.dumps(images, indent=4)) 
        for image in images['Images']:
            image_id = image['ImageId']

            creation_datetime = datetime.datetime.strptime(image['CreationDate'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc) # 이미지 생성일인 CreationDate 를 가져와 변수로 저장

            # Name 태그 가져오기
            name_tag = next((tag['Value'] for tag in image.get('Tags', []) if tag['Key'] == 'Name'), 'N/A')
            
            if creation_datetime < expire_date: # 생성일이 만료일 보다 작을 경우 (만료일이 생성일 보다 클 경우) 즉 14일 이상 경과할 경우
                #print(f"Deregistering AMI: {image_id} (Created: {creation_datetime})")
                response = client.deregister_image(ImageId=image_id) # 실제 AMI 등록 취소 진행 부분
                #print(response)
                time.sleep(2)

            # 스냅샷 조회 시 Description에 AMI ID가 포함된 것만 필터링
            snapshots = client.describe_snapshots(
                Filters=[
                    {
                        'Name': 'description',
                        'Values': [f'* for {image_id}']  # Description에 AMI ID가 포함된 스냅샷만 가져옴
                    }
                ],
                OwnerIds=['self']
            )
            # 연결된 스냅샷도 함께 삭제
            for snapshot in snapshots['Snapshots']:
                snapshot_id = snapshot['SnapshotId'] # 리스트의 Snapshot 중 ID 만 추출함
                # 스냅샷 시작 시간도 타임존 붙여서 aware datetime으로
                snapshot_creation_datetime = snapshot['StartTime'].replace(tzinfo=timezone.utc)
                expire_date = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=days_old)

                # 위에서 만든 expire_date 재사용
                if snapshot_creation_datetime < expire_date:
                    client.delete_snapshot(SnapshotId=snapshot_id)  # 해당 스냅샷 삭제
                    logger.info(f"Deleting Snapshot: {snapshot_id} (Description contains AMI ID: {image_id})")
                    self.ami_delete_webhook_post(snapshot_id, image_id, name_tag)
                    time.sleep(2)

        
     



def lambda_handler(event, context):

    body = json.loads(event['body'])
    data = body['data'].strip()
    instance_name_list = data.split()
    
    magement_ami = management_image_in_deploy(
        instance_name_list = instance_name_list,
        create_webhook_url = 'WebHook URL',
        delete_webhook_url = 'WebHook URL',
        ami_name = ''
    )
    magement_ami.ami_create_webhook_post()
    magement_ami.create_image()
    magement_ami.old_image_delete()
