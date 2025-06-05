import requests
import json
import logging
import boto3

# 로그 설정 ()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

'''
Kafka Lag을 체크하는 Get 요청을 보내는 Class
'''
class check_lag():

    '''
    생성자 메서드 생성
    __init__ 으로 변수 생성 및 초기화
    '''
    def __init__(self, url, query):
        self.url = url
        self.query = query

    '''
    URL 및 쿼리 변수를 이용해 HTTP 요청을 보내는 메서드 생성
    '''
    def get_ep(self):
        # 여기의 params 는 임의로 정한 딕셔너리 이름
        # 쿼리를 딕셔너리형태로 params 라는 변수에 저장
        params = {
            'query': self.query
        }
        try:
            # 실제 요청을 보내는 부분. 여기의 'parmas='는 필수규칙
            r = requests.get(self.url, params=params)
            r.raise_for_status()# HTTP 200이 아닐 경우 예외 발생 (requets 모듈 내장함수)
            j = r.json() # 응답을 json 형태로 받음
            self.status_code = r.status_code # status code 받기
            logger.debug("Get Data Log Kafka LAG")
            return j
            
            # 대중적으로 많이 나오는 에러코드 예외처리
        except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
            logger.critical(f"Failed Get Log Kafka LAG: {e}")
            return None

    
'''
ASG 수량 체크 하는 클래스
'''
class asg_check():
    asg = boto3.client('autoscaling')
    def __init__(self, asg_name):
        self.asg_name = asg_name
        
    def get_capacity(self):
        describe = self.asg.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        maxsize = describe['AutoScalingGroups'][0]['MaxSize']
        minsize = describe['AutoScalingGroups'][0]['MinSize']
        desiredcapacity = describe['AutoScalingGroups'][0]['DesiredCapacity']
        return maxsize, minsize, desiredcapacity

'''
ASG 수량 조절 하는 클래스
'''
class asg_instance_capacity_modify():
    def __init__(self, modified_count, asg_name):
        self.modified_count = modified_count
        self.asg_name = asg_name

    def asg_modify(self):
        logger.info(f"Modify ASG Capacity : {self.modified_count}")
        asg = boto3.client('autoscaling')
        try:
            minsize = asg.update_auto_scaling_group(
                AutoScalingGroupName=self.asg_name,
                MinSize=self.modified_count,
                NewInstancesProtectedFromScaleIn=False            
            )
            desired_capacity = asg.set_desired_capacity(
                AutoScalingGroupName=self.asg_name,
                DesiredCapacity=self.modified_count,
#                MinSize=self.modified_count,
                HonorCooldown=False
            )
            print("ASG 스케일 조정 성공.")
            return {
                "minsize" : minsize,
                "desired_capacity" : desired_capacity
            }
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            print("ASG 스케일 조정 실패.")
            return None


'''
웹훅 발송 클래스
'''
class webhook():
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def scaleout_webhook_post(self, lag):
        header = {
            'Content-Type': 'application/json'
        }
        data = {
            'body' : f'Log Kafka LAG 이 해소되지 않고 있습니다. ASG로 전환합니다. \n Now LAG : {lag}',
            'connectColor' : '#FAC11B',
            'connectInfo' : [
                {
                    'title' : 'Switching from Karpenter to ASG.',
                    'description' : 'Switch from 0 to 4 instances.'
                }
            ] 
        }
        response_webhook = requests.post(self.webhook_url, headers = header ,json=data)
        return response_webhook

    def scalein_webhook_post(self, lag):
        header = {
            'Content-Type': 'application/json'
        }
        data = {
            'body' : f'Log Kafka LAG 이 해소 되었습니다. Karpenter로 전환합니다. \n Now LAG : {lag}',
            'connectColor' : '#FAC11B',
            'connectInfo' : [
                {
                    'title' : 'Switching from ASG to Karpenter.',
                    'description' : 'Switch from 4 to 0 instances.'
                }
            ] 
        }
        response_webhook = requests.post(self.webhook_url, headers = header ,json=data)
        return response_webhook



def lambda_handler(event, context):
# check_lag 클래스를 상속받아 kafka Lag 가져옴 ( X ) -> check_lag 클래스를 통해 check_lag_instace 객체 생성
    check_lag_instance = check_lag(
        url='Prometheus_EndPoint_URL', 
        query='sum(kafka_consumergroup_lag{topic=~"Kafka_Topic"}) by (consumergroup, topic)'
    )
    result = check_lag_instance.get_ep()
    status_code = check_lag_instance.status_code # status code 가져오기
    # 출력값 json 항목 중 실제 Lag 만 추출
    lag_str = result['data']['result'][0]['value'][1]
    # 최초엔 스트링값으로 가져와서 int 로 전환해줌
    lag = int(lag_str)
    logger.debug(f"Log Kafka Lag : {lag}")
    asg_name = asg_check(
        asg_name = 'ASG Name'
    )
    maxsize, minsize, desired = asg_check.get_capacity(asg_name)
    logger.debug(f"AS-IS ASG Capacity : maxsize : {maxsize}, minsize : {minsize}, desired: {desired}")
    webhook_post = webhook(
        webhook_url = 'WEBHook_URL'
    )
    # 실제 실행 부분
    if lag > 10000000 and desired == 0: # 랙 10M 이상 + 카펜터일 경우 스케일아웃
        scale_out = asg_instance_capacity_modify(
            modified_count = 4,
            asg_name = 'ASG Name',
        )
        logger.info("Produce ING.. Scale Up")
        scale_out.asg_modify()
        webhook_post.scaleout_webhook_post(lag)
        print("스케일 업 완료")
    elif lag < 10000000 and lag > 100000 and desired == 4: # 랙 10M ~ 100k + ASG 일 경우 패스
        logger.debug("Consume ING.. PASS")
        pass
    elif lag > 10000000 and desired >  0 and desired < 4: # 랙 10M 이상 + ASG 1~3대일 경우 4대로 고정
        logger.debug("Consume ING.. BUT less than 4 ASG instances.. Scale Out Start.")
        scale_out.asg_modify()
    elif lag > 10000000 and desired == 4: # 랙 10M 이상 + ASG 4대일 경우 컨슘하게 내비둠
        logger.debug("Consume ING.. ASG already at max (4). PASS.")
        pass
    elif lag < 100000 and desired >= 4: # 랙 100k 이하 + ASG 4대 이상일 경우 스케일 인
        scale_in = asg_instance_capacity_modify(
            modified_count = 0,
            asg_name = 'ASG Name'
        )
        logger.info("Consume Complete.. Scale IN. Switch to Karpenter.")
        webhook_post.scalein_webhook_post(lag)
        scale_in.asg_modify()
    elif lag < 10000000 and lag > 100000 and desired == 0: # 랙 10M ~ 100k + 카펜터일 경우 패스
        print("현재 상태 정상")
        logger.info("현재 상태 정상")
    elif lag < 100000 and desired != 0: # 랙 100k 이하 + ASG에 인스턴스 있을 경우 스케일 인
        scale_in = asg_instance_capacity_modify(
            modified_count = 0,
            asg_name = 'ASG Name'
        )
        logger.info("Consume Complete.. Scale IN. Switch to Karpenter.")
        webhook_post.scalein_webhook_post(lag)
        scale_in.asg_modify()
    elif lag < 100000 and desired == 0: # lag 100k 이하 + 카펜터 일 경우 패스
        logger.debug("Kafka LAG Stable.")
    else:
        logger.error("Lambda Error.")


"""
추가로 할일 
클래스 연결해서 API Gateway 로 POST 하는거 완성
"""