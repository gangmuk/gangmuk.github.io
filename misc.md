---
layout: misc
title: Life
slug: /misc
---

<style>
  .album {
    display: grid;
    /* grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); */
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); /* Adjust size here */
    gap: 16px;
    margin-top: 20px;
  }
  .album-item {
    text-align: center;
    overflow: hidden;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease-in-out;
  }
  .album-item:hover {
    transform: scale(1.05);
  }

  .album-item img {
    width: 100%;
    height: 0;
    padding-bottom: 100%; /* Maintains square ratio */
    object-fit: cover; /* Ensures image covers the square fully */
    display: block; /* Removes inline spacing */
    margin-bottom: 0; /* Removes gap below the image */
  }
  .album-title {
    font-size: 18px;
    font-weight: bold;
    margin: 8px 0 4px;
  }
  .album-description {
    font-size: 14px;
    color: #555;
    margin-bottom: 0 0 8px;
  }
</style>

<div class="album">
  <div class="album-item">
    <img src="/assets/img/kohtao.png" alt="Kohtao">
    <div class="album-title">Freediving</div>
    <div class="album-description">Freediving at Kohtao, Thailand.</div>
    <iframe width="100%" height="200" src="https://www.youtube.com/embed/09qmBdsWRZk?si=V48vRsntdA2aURPw" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
  </div>
  <div class="album-item">
    <img src="/assets/img/surfing.png" alt="Surfing">
    <div class="album-title">Surfing</div>
    <div class="album-description">Surfing at Essaouira, Morocco.</div>
  </div>
</div>
