---
layout: home
profile_picture:
  src: profile2.jpg
  alt: website picture
---

<style>
h2 {
  font-family: inherit; /* Inherit from body instead of 'Times New Roman' */
  font-weight: bold; /* or 'normal' if you prefer */
  font-size: 1.5em;
  color: #000;
}
h3 {
  font-family: inherit;
  font-weight: bold;
}
</style>

<p>
I am a fourth year Ph.D. student at the Computer Science Department of the University of Illinois Urbana-Champaign. I am working with Professor <a href="https://pbg.cs.illinois.edu">Brighten Godfrey</a>, and also closely working with Professor <a href="https://radhikam.web.illinois.edu/">Radhika Mittal</a>. 

Also, I earned my Bachelor and Master at the Computer Science at UNIST, South Korea, working with Professor <a href="https://sites.google.com/site/myeongjae/">Myeongjae Jeon</a>.
</p>

<p>
I am broadly interested in system and networking. 
My current research focuses on cloud infrastructure, specifically for LLM inference. I aim to improve application performance, reduce costs, and enhance reliability by making infrastructure more application-aware. My projects include request routing for microservices in geo-distributed clusters (SLATE), LLM inference routing system (Quicksilver), verification for cluster manager (Kivi), and DNN training co-location framework (Zico).

<!-- All of my works heavily involve K8S and all done in K8S and some with Envoy proxy and Istio service mesh. -->
</p>

Most likely, you can find me on the 3rd floor at Siebel Center for Computer Science at Urbana, IL (or at a cafe in Urbana-Champaign)<br>

<p>
 <a href="http://linkedin.com/in/gangmuk">LinkedIn</a>, <a href="http://github.com/gangmuk">GitHub</a>, <a href="http://gangmuk.github.io/cv.pdf">CV</a>
</p>


## News!
<style>
  .news-item {
    display: flex;
    margin-bottom: 8px;
  }
  .news-date {
    min-width: 100px;
    font-weight: bold;
    color: #666;
    font-size: 0.9em;
    padding-top: 2px;
  }
  .news-content {
    flex: 1;
    color: #333;
  }
</style>

<div class="news-list">
  <div class="news-item">
    <div class="news-date">Jul, 2025</div>
    <div class="news-content">
      <em><b>SLATE: Service Layer Traffic Engineering</b></em> was accepted to <em>NSDI '26</em>!
    </div>
  </div>

  <div class="news-item">
    <div class="news-date">Jan, 2025</div>
    <div class="news-content">
      Started internship at Bytedance, Compute Infra team, Seattle. Cloud-native infrastructure for GenAI inference. (project <a href="https://github.com/vllm-project/aibrix">AIBrix</a>)
    </div>
  </div>

  <div class="news-item">
    <div class="news-date">Sep, 2024</div>
    <div class="news-content">
      <em><b>Opportunities and Challenges in Service Layer Traffic Engineering</b></em> was accepted to <a href="https://conferences.sigcomm.org/hotnets/2024/accepted.html">HotNets '24</a>! See you at Irvine, CA!
    </div>
  </div>

  <div class="news-item">
    <div class="news-date">Apr, 2024</div>
    <div class="news-content">
      <em><b>Kivi</b></em> was accepted to USENIX ATC '24! Thank USENIX ATC for the travel grant.
    </div>
  </div>

  <div class="news-item">
    <div class="news-date">Nov, 2023</div>
    <div class="news-content">
      Gave a talk at KubeCon '23 about <em>Kivi</em>, Chicago, IL. <a href="https://www.youtube.com/watch?v=EEj8ptQmZmY&t=1s">talk</a>
    </div>
  </div>

  <div class="news-item">
    <div class="news-date">Nov, 2023</div>
    <div class="news-content">
      Gave a talk at EnvoyCon '23 about <em>SLATE</em>, Chicago, IL. <a href="https://youtu.be/iBQaaGBQVMA?si=8dB91JyVAFoTUVUj">talk</a>
    </div>
  </div>

  <div class="news-item">
    <div class="news-date">Mar, 2023</div>
    <div class="news-content">
      Gave a talk at IstioCon '23 about <em>SLATE</em>, Virtual.
    </div>
  </div>
</div>




## Publication
<style>
  .pub-item {
    margin-bottom: 12px;
  }
  .pub-title {
    /* font-weight: bold; */
    color: #000;
    font-size: 1.0em;
  }
  .pub-venue-badge {
    /* font-weight: bold; */
    color: #000;
    margin-right: 6px;
  }
  .pub-authors {
    margin: 0px 0 2px 0;
    color: #333;
    display: block;
  }
  .pub-conf-details {
    font-style: italic;
    color: #666;
    font-size: 0.9em;
    display: block;
  }
  .pub-note {
    font-size: 0.9em;
    color: #666;
    margin-top: 1px;
  }
</style>

<div class="pub-list">
  <div class="pub-item">
    <div class="pub-title">
      <span class="pub-venue-badge">[NSDI '26]</span>SLATE: Service Layer Traffic Engineering
    </div>
    <div class="pub-authors"><i><ins>Gangmuk Lim</ins><sup>*</sup>, Aditya Prerepa<sup>*</sup>, Brighten Godfrey, Radhika Mittal</i></div>
    <div class="pub-conf-details">In Proceedings of the 23rd USENIX Symposium on Networked Systems Design and Implementation (NSDI'26), Renton, WA, May 2026.</div>
    <div class="pub-note">(* co-first author)</div>
  </div>

  <div class="pub-item">
    <div class="pub-title">
      <span class="pub-venue-badge">[arXiv]</span>AIBrix: Towards Scalable, Cost-Effective Large Language Model Inference Infrastructure
    </div>
    <div class="pub-authors"><i>Jiaxin Shan, Varun Gupta, Le Xu, Haiyang Shi, Jingyuan Zhang, Ning Wang, Linhui Xu, Rong Kang, Tongping Liu, Yifei Zhang, Yiqing Zhu, Shuowei Jin, <ins>Gangmuk Lim</ins>, Binbin Chen, Zuzhi Chen, Xiao Liu, Xin Chen, Kante Yin, Chak-Pong Chung, Chenyu Jiang, Yicheng Lu, Jianjun Chen, Caixue Lin, Wu Xiang, Rui Shi, Liguang Xie</i></div>
    <div class="pub-conf-details">arXiv:2504.03648, March 2025.</div>
  </div>

  <div class="pub-item">
    <div class="pub-title">
      <span class="pub-venue-badge">[HotNets '24]</span>Opportunities and Challenges in Service Layer Traffic Engineering
    </div>
    <div class="pub-authors"><i><ins>Gangmuk Lim</ins><sup>*</sup>, Aditya Prerepa<sup>*</sup>, Brighten Godfrey, Radhika Mittal</i></div>
    <div class="pub-note">(*co-first author)</div>
    <div class="pub-conf-details">In Proceedings of the 23rd ACM Workshop on Hot Topics in Networks (HotNets'24), Irvine, California, November 2024.</div>
  </div>

  <div class="pub-item">
    <div class="pub-title">
      <span class="pub-venue-badge">[USENIX ATC '24]</span>Kivi: Verification for Cluster Management
    </div>
    <div class="pub-authors"><i>Bingzhe Liu, <ins>Gangmuk Lim</ins>, Ryan Beckett, P. Brighten Godfrey.</i></div>
    <div class="pub-conf-details">In Proceedings of the 2024 USENIX Annual Technical Conference (USENIX ATC'24), Santa Clara, CA, July 2024.</div>
  </div>

  <div class="pub-item">
    <div class="pub-title">
      <span class="pub-venue-badge">[USENIX ATC '21]</span>Zico: Efficient GPU Memory Sharing for Concurrent DNN Training
    </div>
    <div class="pub-authors"><i><ins>Gangmuk Lim</ins>, Jeongseob Ahn, Wencong Xiao, Youngjin Kwon, Myeongjae Jeon.</i></div>
    <div class="pub-conf-details">In Proceedings of the 2021 USENIX Annual Technical Conference (USENIX ATC'21), July 2021.</div>
  </div>

  <div class="pub-item">
    <div class="pub-title">
      <span class="pub-venue-badge">[ICDE '20]</span>Approximate Quantiles for Data Center Telemetry Monitoring <span style="font-weight: normal; font-size: 0.9em;">(short paper)</span>
    </div>
    <div class="pub-authors"><i><ins>Gangmuk Lim</ins>, Myeongjae Jeon, Stavros Volos, Mohamed Hassan, Ze Jin.</i></div>
    <div class="pub-conf-details">In Proceedings of the 36th IEEE International Conference on Data Engineering (ICDE'20), Dallas, Texas, April 2020.</div>
  </div>
</div>

## Experiences

<style>
.experience-item {
  display: flex;
  margin-bottom: 20px;
}
.experience-date {
  min-width: 160px;
  font-weight: bold;
  color: #666;
}
.experience-details {
  flex: 1;
}
.experience-role {
  font-weight: bold;
  color: #333;
}
.experience-company {
  color: #000;
}
.experience-location {
  color: #666;
  font-style: italic;
}
</style>

<div class="experience-list">
  <div class="experience-item">
    <div class="experience-date">Jan 2025 - Jun 2025</div>
    <div class="experience-details">
      <div class="experience-role">Research Intern, Compute Infra Team</div>
      <div class="experience-company">Bytedance</div>
      <div class="experience-location">Seattle, WA</div>
    </div>
  </div>

  <div class="experience-item">
    <div class="experience-date">Jul 2021 - Apr 2022</div>
    <div class="experience-details">
      <div class="experience-role">Software Engineer</div>
      <div class="experience-company">Rebellions</div>
      <div class="experience-location">Seongnam, Korea</div>
    </div>
  </div>

  <div class="experience-item">
    <div class="experience-date">Jun 2018 - Aug 2018</div>
    <div class="experience-details">
      <div class="experience-role">Research Intern, Media Lab</div>
      <div class="experience-company">Ghent University</div>
      <div class="experience-location">Ghent, Belgium</div>
    </div>
  </div>
</div>

## Other Facts about me

### Sports
I love doing all different kinds of sports such as basketball, running, swimming, freediving, tennis, and more. So, half of my joints have been gone...
<br>

### Backpacking
In the past, I enjoyed rather extreme backpacking trips, mostly solo trips. Extreme as in no plan, no reservation (hotel or transportation), just a backpack and taking a flight to a new place by myself, not knowing where to go other than the first city. It is like an unopened gift box. I did it intentionally to meet as many new and diverse people as possible and hidden gems in the world. And it definitely worked.
This extreme style of traveling started from a solo backpacking that I made at 15 years old to Japan where I lost all the cashes I had and cried on a random street.
The places I have been are from Japan, Thailand, India, Nepal, Myammar, Cambodia, Morroco, all Europe countries except for the north part, etc. 
<br>