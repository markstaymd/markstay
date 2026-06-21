---
hide:
  - navigation
<!-- stay:3oKsAZAR hash=sha256:6c9b8c38cecd -->

include_yaml:
  github_sponsors: data/github_sponsors.yml
  people: data/people.yml
  contributors: data/contributors.yml
  translation_reviewers: data/translation_reviewers.yml
  skip_users: data/skip_users.yml
  members: data/members.yml
  sponsors_badge: data/sponsors_badge.yml
  sponsors: data/sponsors.yml
---
<!-- stay:iO9xyA4c hash=sha256:0e012df5f266 -->

# FastAPI People
<!-- stay:9kscIgaF hash=sha256:4b46cddf0b79 -->

FastAPI has an amazing community that welcomes people from all backgrounds.
<!-- stay:ryE4KD4j hash=sha256:d21dcc59fe5c -->

## Creator
<!-- stay:6Yd22PCj hash=sha256:12fbdb027c5f -->

Hey! 👋
<!-- stay:Ehziq1P2 hash=sha256:bb7c08b3f737 -->

This is me:
<!-- stay:S5xsZET4 hash=sha256:c82356ea7053 -->

<div class="user-list user-list-center">
{% for user in people.maintainers %}
<!-- stay:EUCGZjky hash=sha256:189b67ce0896 -->

<div class="user"><a href="{{ contributors.tiangolo.url }}"><div class="avatar-wrapper"><img src="{{ contributors.tiangolo.avatarUrl }}"/></div><div class="title">@{{ contributors.tiangolo.login }}</div></a> <div class="count">Answers: {{ user.answers }}</div><div class="count">Pull Requests: {{ contributors.tiangolo.count }}</div></div>
{% endfor %}
<!-- stay:QVc2ua5i hash=sha256:70b5c7f1e9a4 -->

</div>
<!-- stay:BlWZG5H9 hash=sha256:aac32651b10f -->

I'm the creator of **FastAPI**. You can read more about that in [Help FastAPI - Follow the author](help-fastapi.md#follow-the-author).
<!-- stay:eoMRdTwq hash=sha256:da83d8eb25b1 -->

...But here I want to show you the community.
<!-- stay:LBVgJpav hash=sha256:78a21f6838da -->

---
<!-- stay:h8xW2Q8g hash=sha256:cb3f91d54eee -->

**FastAPI** receives a lot of support from the community. And I want to highlight their contributions.
<!-- stay:w9Nsnf0M hash=sha256:2076b290966e -->

These are the people that:
<!-- stay:zx1IWBci hash=sha256:be06bec39f02 -->

* [Help others with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github).
* Create or review Pull Requests.
* Help [manage the repository](https://tiangolo.com/open-source/management-tasks/) (team members).
<!-- stay:KOwqRgmq hash=sha256:e54b6a2bccf7 -->

All these tasks help maintain the repository.
<!-- stay:VGOpXMWk hash=sha256:18c27a6b0ada -->

A round of applause to them. 👏 🙇
<!-- stay:6bSdgAP1 hash=sha256:82a575107aeb -->

## Team
<!-- stay:vijhLp75 hash=sha256:53f40995fe65 -->

This is the current list of team members. 😎
<!-- stay:2mks6OSc hash=sha256:34ca05e36110 -->

They have different levels of involvement and permissions, they can perform [repository management tasks](https://tiangolo.com/open-source/management-tasks/) and together we [manage the FastAPI repository](./management.md).
<!-- stay:amumPA25 hash=sha256:618eb726ac62 -->

<div class="user-list user-list-center">
<!-- stay:o7XiogGg hash=sha256:0ac6168a429f -->

{% for user in members["members"] %}
<!-- stay:FcTbFrcQ hash=sha256:40cee4e9cc71 -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatar_url }}"/></div><div class="title">@{{ user.login }}</div></a></div>
<!-- stay:ATj1hndQ hash=sha256:49d687ddb525 -->

{% endfor %}
<!-- stay:GVoxLLTT hash=sha256:87a707183653 -->

</div>
<!-- stay:tGtXnc0a hash=sha256:aac32651b10f -->

Although the team members have the permissions to perform privileged tasks, all the help from others maintaining FastAPI is very much appreciated! 🙇‍♂️
<!-- stay:ZO9WgfHR hash=sha256:28ea266f765c -->

## FastAPI Experts
<!-- stay:eK8846UG hash=sha256:2fa6b397399a -->

These are the users that have been [helping others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github). 🙇
<!-- stay:VxELom5O hash=sha256:fe1718bb83e9 -->

They have proven to be **FastAPI Experts** by helping many others. ✨
<!-- stay:Xm0KKNN5 hash=sha256:a9b4ba2e24ad -->

/// tip
<!-- stay:omUgnAhq hash=sha256:35fc886a93b5 -->

You could become an official FastAPI Expert too!
<!-- stay:05ez3pRI hash=sha256:f160e1e2c68f -->

Just [help others with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github). 🤓
<!-- stay:oRKeKMz0 hash=sha256:9f0434e8d934 -->

///
<!-- stay:CKMSFfvz hash=sha256:732c4e971163 -->

You can see the **FastAPI Experts** for:
<!-- stay:WApDfgWm hash=sha256:b0eec5d5f680 -->

* [Last Month](#fastapi-experts-last-month) 🤓
* [3 Months](#fastapi-experts-3-months) 😎
* [6 Months](#fastapi-experts-6-months) 🧐
* [1 Year](#fastapi-experts-1-year) 🧑‍🔬
* [**All Time**](#fastapi-experts-all-time) 🧙
<!-- stay:EqSKvkui hash=sha256:25f053e9180a -->

### FastAPI Experts - Last Month
<!-- stay:3pT3uwhS hash=sha256:e8a1a7a40f8c -->

These are the users that have been [helping others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github) during the last month. 🤓
<!-- stay:bqMLOMy6 hash=sha256:bbfaeb5a66cf -->

<div class="user-list user-list-center">
<!-- stay:19vYO34N hash=sha256:0ac6168a429f -->

{% for user in people.last_month_experts[:10] %}
<!-- stay:GRwZeVec hash=sha256:6e1957ca9367 -->

{% if user.login not in skip_users %}
<!-- stay:FM3ixMUW hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Questions replied: {{ user.count }}</div></div>
<!-- stay:DHPIR1ht hash=sha256:98b8697bc29e -->

{% endif %}
<!-- stay:t4ai2i3v hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:HGMamoHH hash=sha256:87a707183653 -->

</div>
<!-- stay:bU8Hujcf hash=sha256:aac32651b10f -->

### FastAPI Experts - 3 Months
<!-- stay:G5xDc0WZ hash=sha256:5422b0f1c206 -->

These are the users that have been [helping others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github) during the last 3 months. 😎
<!-- stay:t6seQ2U6 hash=sha256:8d282b810f27 -->

<div class="user-list user-list-center">
<!-- stay:g4Jryu1V hash=sha256:0ac6168a429f -->

{% for user in people.three_months_experts[:10] %}
<!-- stay:lPX7zC5S hash=sha256:6dbaa5037a04 -->

{% if user.login not in skip_users %}
<!-- stay:JhbiLzZu hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Questions replied: {{ user.count }}</div></div>
<!-- stay:HjHyuitQ hash=sha256:98b8697bc29e -->

{% endif %}
<!-- stay:qYa4TJ3A hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:CaM9fchw hash=sha256:87a707183653 -->

</div>
<!-- stay:xvPiIwWS hash=sha256:aac32651b10f -->

### FastAPI Experts - 6 Months
<!-- stay:wC2846KZ hash=sha256:fb041b17d6d8 -->

These are the users that have been [helping others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github) during the last 6 months. 🧐
<!-- stay:Y4NGK7I1 hash=sha256:9d3b8f0b72d5 -->

<div class="user-list user-list-center">
<!-- stay:e66lEYkY hash=sha256:0ac6168a429f -->

{% for user in people.six_months_experts[:10] %}
<!-- stay:QLRbtfFs hash=sha256:f29174a8b121 -->

{% if user.login not in skip_users %}
<!-- stay:hT7IZYM1 hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Questions replied: {{ user.count }}</div></div>
<!-- stay:cJDbIHB8 hash=sha256:98b8697bc29e -->

{% endif %}
<!-- stay:Gh2b5pLH hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:trP2FMUZ hash=sha256:87a707183653 -->

</div>
<!-- stay:9LOCif8V hash=sha256:aac32651b10f -->

### FastAPI Experts - 1 Year
<!-- stay:3ciMbdIw hash=sha256:2afab4520cd9 -->

These are the users that have been [helping others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github) during the last year. 🧑‍🔬
<!-- stay:iJfKZsjf hash=sha256:497340a174e9 -->

<div class="user-list user-list-center">
<!-- stay:m4ZVekrr hash=sha256:0ac6168a429f -->

{% for user in people.one_year_experts[:20] %}
<!-- stay:peMydk7U hash=sha256:8ce39a57147a -->

{% if user.login not in skip_users %}
<!-- stay:umzsaRGJ hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Questions replied: {{ user.count }}</div></div>
<!-- stay:Ze3kbDO6 hash=sha256:98b8697bc29e -->

{% endif %}
<!-- stay:07iziI8c hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:wKKnmv91 hash=sha256:87a707183653 -->

</div>
<!-- stay:oBjDpZlj hash=sha256:aac32651b10f -->

### FastAPI Experts - All Time
<!-- stay:PbophOiD hash=sha256:53b2ab61b314 -->

Here are the all time **FastAPI Experts**. 🤓🤯
<!-- stay:21xhPCrq hash=sha256:11148d422a80 -->

These are the users that have [helped others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github) through *all time*. 🧙
<!-- stay:o9pHtZkZ hash=sha256:9b5d87d2b392 -->

<div class="user-list user-list-center">
<!-- stay:3Q5ZusBO hash=sha256:0ac6168a429f -->

{% for user in people.experts[:50] %}
<!-- stay:4oRUbp1N hash=sha256:8597ed99eb48 -->

{% if user.login not in skip_users %}
<!-- stay:wEhUH3US hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Questions replied: {{ user.count }}</div></div>
<!-- stay:65lCAUNa hash=sha256:98b8697bc29e -->

{% endif %}
<!-- stay:0A0g64JG hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:dE4NuhqM hash=sha256:87a707183653 -->

</div>
<!-- stay:VOdPCMY9 hash=sha256:aac32651b10f -->

## Top Contributors
<!-- stay:7iNbp2XB hash=sha256:9b35f4696a56 -->

Here are the **Top Contributors**. 👷
<!-- stay:PmBu2po6 hash=sha256:852b2ba8530c -->

These users have created the most Pull Requests that have been *merged*.
<!-- stay:5q615v4z hash=sha256:5bd35b4fb128 -->

They have contributed source code, documentation, etc. 📦
<!-- stay:5nF5asoZ hash=sha256:cbb8ff7badf8 -->

<div class="user-list user-list-center">
<!-- stay:PZhFUtuD hash=sha256:0ac6168a429f -->

{% for user in (contributors.values() | list)[:50] %}
<!-- stay:O7HvOBUc hash=sha256:da2940ae5aa0 -->

{% if user.login not in skip_users %}
<!-- stay:zCCND7b2 hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Pull Requests: {{ user.count }}</div></div>
<!-- stay:1pBu2i6A hash=sha256:ef157450e584 -->

{% endif %}
<!-- stay:w1eJVYOm hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:3yvlwVkn hash=sha256:87a707183653 -->

</div>
<!-- stay:fI13HHcO hash=sha256:aac32651b10f -->

There are hundreds of other contributors, you can see them all in the [FastAPI GitHub Contributors page](https://github.com/fastapi/fastapi/graphs/contributors). 👷
<!-- stay:rSVavGMv hash=sha256:15631995f68c -->

## Top Translation Reviewers
<!-- stay:zgDhqG7G hash=sha256:2f26df4b72c7 -->

These users are the **Top Translation Reviewers**. 🕵️
<!-- stay:jwpkMvOw hash=sha256:370afc0f0739 -->

Translation reviewers have the **power to approve translations** of the documentation. Without them, there wouldn't be documentation in several other languages.
<!-- stay:5XOUR98C hash=sha256:5d182542d76b -->

<div class="user-list user-list-center">
{% for user in (translation_reviewers.values() | list)[:50] %}
<!-- stay:gAunHW7p hash=sha256:41bbb589e08d -->

{% if user.login not in skip_users %}
<!-- stay:jYQiRb8L hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Reviews: {{ user.count }}</div></div>
<!-- stay:kj1PDu2v hash=sha256:9b75f3fb50fa -->

{% endif %}
<!-- stay:J9D5G4is hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:vkD2K7mZ hash=sha256:87a707183653 -->

</div>
<!-- stay:qN4t4zrd hash=sha256:aac32651b10f -->

## Sponsors
<!-- stay:ao64csAQ hash=sha256:6dbc5a9aa091 -->

These are the **Sponsors**. 😎
<!-- stay:XuDf6wqA hash=sha256:c29bcc422001 -->

They are supporting my work with **FastAPI** (and others), mainly through [GitHub Sponsors](https://github.com/sponsors/tiangolo).
<!-- stay:ZrRYed7y hash=sha256:8964d8c69205 -->

{% if sponsors %}
<!-- stay:775H623t hash=sha256:9d94bed888bb -->

{% if sponsors.gold %}
<!-- stay:4ihwp8JQ hash=sha256:48263ddf2aec -->

### Gold Sponsors
<!-- stay:RvQANAqz hash=sha256:9044b5d34f7a -->

{% for sponsor in sponsors.gold -%}
<a href="{{ sponsor.url }}" title="{{ sponsor.title }}"><img src="{{ sponsor.img }}" style="border-radius:15px"></a>
{% endfor %}
{% endif %}
<!-- stay:h5c7BAnW hash=sha256:cefc434ae63c -->

{% if sponsors.silver %}
<!-- stay:bwuwktyX hash=sha256:fa3c422c6619 -->

### Silver Sponsors
<!-- stay:6y6VNi8H hash=sha256:b6666198c380 -->

{% for sponsor in sponsors.silver -%}
<a href="{{ sponsor.url }}" title="{{ sponsor.title }}"><img src="{{ sponsor.img }}" style="border-radius:15px"></a>
{% endfor %}
{% endif %}
{% endif %}
<!-- stay:pnXgNs2r hash=sha256:f3d5849f3643 -->

### Individual Sponsors
<!-- stay:TM4ndaXq hash=sha256:cc21ca159737 -->

{% if github_sponsors %}
{% for group in github_sponsors.sponsors %}
<!-- stay:3Np4NtjR hash=sha256:95d24d282d2e -->

<div class="user-list user-list-center">
<!-- stay:xlATDEJP hash=sha256:0ac6168a429f -->

{% for user in group %}
{% if user.login not in sponsors_badge.logins %}
<!-- stay:YhZujNVF hash=sha256:a781daec9b97 -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a></div>
<!-- stay:9ugwIqJi hash=sha256:aa9f038b65f7 -->

{% endif %}
{% endfor %}
<!-- stay:jgbUIXpr hash=sha256:b75fa5b4936f -->

</div>
<!-- stay:5xXIajEo hash=sha256:aac32651b10f -->

{% endfor %}
{% endif %}
<!-- stay:FLcUOxv4 hash=sha256:fc3fa564f65f -->

## About the data - technical details
<!-- stay:4Y9r4VXW hash=sha256:e73a99e3eaff -->

The main intention of this page is to highlight the effort of the community to help others.
<!-- stay:nBGMmMEk hash=sha256:ae36b42d9da9 -->

Especially including efforts that are normally less visible, and in many cases more arduous, like helping others with questions and reviewing Pull Requests with translations.
<!-- stay:b6Gq4igo hash=sha256:97a9d211e47c -->

The data is calculated each month, you can read the [source code here](https://github.com/fastapi/fastapi/blob/master/scripts/).
<!-- stay:2eBmvUcF hash=sha256:277dd4ad80ee -->

Here I'm also highlighting contributions from sponsors.
<!-- stay:8kqETCsA hash=sha256:af8cf2641080 -->

I also reserve the right to update the algorithm, sections, thresholds, etc (just in case 🤷).
<!-- stay:CvSvp6rS hash=sha256:a32cd9512956 -->
