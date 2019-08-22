---
title: "Welcome to K's Research Note!"
date: 2019-08-22 10:40:28 -0400
categories: Intro update
---

Getting Memory Log provided by Tensorflow
=========================================

#### 1.	run하고자 하는 python 코드 맨 위에 아래 코드 추가
```python
import os
os.environ['TF_CPP_MIN_VLOG_LEVEL'] = '1'
```
이라고 적어 준다.
현재 우리가 필요한 메모리 로그는 '1'이면 출력이 된다.

BERT의 경우 run_pretraining.py를 돌릴 것이기 때문에 run_pretraining.py의 맨 위에 위 코드를 추가해주면 된다.
그리고 run을 하면 해당 레벨의 로그들이 stderr로 터미널에 출력된다.

#### 2.	해당 메모리 로그 출력 관련 파일
```sh
/tensorflow/core/framework/log_memory.h
```

달려있는 주석 설명
```python
25 // LogMemory contains methods for recording memory allocations and
26 // frees, associating each allocation with a step identified by a
27 // process-wide id. For now, logging is enabled whenever VLOG_IS_ON(1)
28 // for the log_memory module.
```

#### 3. 각 레벨 따른 로그 출력에 관한 설명
```sh
/tensorflow/examples/android/jni/object_tracking/logging.h
```

```python
44 // Log levels equivalent to those defined by
45 // third_party/tensorflow/core/platform/logging.h
46 const int INFO = 0;            // base_logging::INFO;
47 const int WARNING = 1;         // base_logging::WARNING;
48 const int ERROR = 2;           // base_logging::ERROR;
49 const int FATAL = 3;           // base_logging::FATAL;
50 const int NUM_SEVERITIES = 4;  // base_logging::NUM_SEVERITIES;
```

#### 4.	LOG 와 VLOG 차이
-  'TF_CPP_MIN_LOG_LEVEL' os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 는 ERROR, FATAL, NUM_SEVERITIES를 출력해준다. 숫자가 커지면 더 적은 로그가 출력된다.
#####
- 'TF_CPP_MIN_VLOG_LEVEL' os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2 는 ERROR, WARNING, INFO를 출력해준다. 숫자가 커지면 더 많은 로그가 출력된다.
