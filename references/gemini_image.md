Gemini 모델은 처음부터 멀티모달로 설계되어 전문 ML 모델을 학습하지 않고도 이미지 캡셔닝, 분류, 시각적 질의 응답 등 다양한 이미지 처리 및 컴퓨터 비전 작업을 수행할 수 있습니다.

도움말: Gemini 모델 (2.0 이상)은 일반적인 멀티모달 기능 외에도 추가 학습을 통해 객체 감지 및 세분화와 같은 특정 사용 사례에 대해 정확도가 향상되었습니다. 자세한 내용은 기능 섹션을 참고하세요.
Gemini에 이미지 전달
다음 두 가지 방법을 사용하여 Gemini에 이미지를 입력으로 제공할 수 있습니다.

인라인 이미지 데이터 전달: 작은 파일 (프롬프트를 포함한 총 요청 크기가 20MB 미만)에 적합합니다.
File API를 사용하여 이미지 업로드: 대용량 파일에 적합하며 여러 요청에서 이미지를 재사용하는 데 적합합니다.
인라인 이미지 데이터 전달
generateContent에 대한 요청에서 인라인 이미지 데이터를 전달할 수 있습니다. Base64 인코딩 문자열로 이미지 데이터를 제공하거나 언어에 따라 로컬 파일을 직접 읽을 수 있습니다.

다음 예에서는 로컬 파일에서 이미지를 읽고 처리할 generateContent API에 전달하는 방법을 보여줍니다.

Python
자바스크립트
Go
REST

  from google.genai import types

  with open('path/to/small-sample.jpg', 'rb') as f:
      image_bytes = f.read()

  response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
      types.Part.from_bytes(
        data=image_bytes,
        mime_type='image/jpeg',
      ),
      'Caption this image.'
    ]
  )

  print(response.text)
다음 예와 같이 URL에서 이미지를 가져와 바이트로 변환하고 generateContent에 전달할 수도 있습니다.

Python
자바스크립트
Go
REST

from google import genai
from google.genai import types

import requests

image_path = "https://goo.gle/instrument-img"
image_bytes = requests.get(image_path).content
image = types.Part.from_bytes(
  data=image_bytes, mime_type="image/jpeg"
)

client = genai.Client()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=["What is this image?", image],
)

print(response.text)
참고: 인라인 이미지 데이터는 총 요청 크기 (텍스트 프롬프트, 시스템 지침, 인라인 바이트)를 20MB로 제한합니다. 더 큰 요청의 경우 File API를 사용하여 이미지 파일을 업로드하세요. 파일 API는 동일한 이미지를 반복적으로 사용하는 시나리오에도 더 효율적입니다.
File API를 사용하여 이미지 업로드
큰 파일의 경우 또는 동일한 이미지 파일을 반복적으로 사용하려면 Files API를 사용하세요. 다음 코드는 이미지 파일을 업로드한 다음 generateContent 호출에서 파일을 사용합니다. 자세한 내용과 예시는 파일 API 가이드를 참고하세요.

Python
자바스크립트
Go
REST

from google import genai

client = genai.Client()

my_file = client.files.upload(file="path/to/sample.jpg")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[my_file, "Caption this image."],
)

print(response.text)
여러 이미지로 프롬프트하기
contents 배열에 이미지 Part 객체를 여러 개 포함하여 단일 프롬프트에 여러 이미지를 제공할 수 있습니다. 인라인 데이터(로컬 파일 또는 URL)와 파일 API 참조가 혼합될 수 있습니다.

Python
자바스크립트
Go
REST

from google import genai
from google.genai import types

client = genai.Client()

# Upload the first image
image1_path = "path/to/image1.jpg"
uploaded_file = client.files.upload(file=image1_path)

# Prepare the second image as inline data
image2_path = "path/to/image2.png"
with open(image2_path, 'rb') as f:
    img2_bytes = f.read()

# Create the prompt with text and multiple images
response = client.models.generate_content(

    model="gemini-2.5-flash",
    contents=[
        "What is different between these two images?",
        uploaded_file,  # Use the uploaded file reference
        types.Part.from_bytes(
            data=img2_bytes,
            mime_type='image/png'
        )
    ]
)

print(response.text)
객체 감지
Gemini 2.0부터는 이미지에서 객체를 감지하고 경계 상자 좌표를 가져오도록 모델이 추가로 학습됩니다. 이미지 크기에 상대적인 좌표는 [0, 1000]으로 조정됩니다. 원본 이미지 크기에 따라 이러한 좌표의 크기를 조정해야 합니다.

Python

from google import genai
from google.genai import types
from PIL import Image
import json

client = genai.Client()
prompt = "Detect the all of the prominent items in the image. The box_2d should be [ymin, xmin, ymax, xmax] normalized to 0-1000."

image = Image.open("/path/to/image.png")

config = types.GenerateContentConfig(
  response_mime_type="application/json"
  )

response = client.models.generate_content(model="gemini-2.5-flash",
                                          contents=[image, prompt],
                                          config=config
                                          )

width, height = image.size
bounding_boxes = json.loads(response.text)

converted_bounding_boxes = []
for bounding_box in bounding_boxes:
    abs_y1 = int(bounding_box["box_2d"][0]/1000 * height)
    abs_x1 = int(bounding_box["box_2d"][1]/1000 * width)
    abs_y2 = int(bounding_box["box_2d"][2]/1000 * height)
    abs_x2 = int(bounding_box["box_2d"][3]/1000 * width)
    converted_bounding_boxes.append([abs_x1, abs_y1, abs_x2, abs_y2])

print("Image size: ", width, height)
print("Bounding boxes:", converted_bounding_boxes)

참고: 모델은 '이 이미지의 모든 녹색 객체의 경계 상자를 표시해 줘'와 같은 맞춤 안내에 따라 경계 상자를 생성하는 기능도 지원합니다. '알레르기 유발 물질이 포함된 상품에 라벨을 지정해 줘'와 같은 맞춤 라벨도 지원합니다.
자세한 예는 Gemini Cookbook의 다음 노트북을 참고하세요.

2D 공간 이해 노트북
실험용 3D 포인팅 노트북