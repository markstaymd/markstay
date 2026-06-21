---
hide:
  - navigation
<!-- stay:OAxgBZBk hash=sha256:6c9b8c38cecd -->

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
<!-- stay:c1of9ycV hash=sha256:0e012df5f266 -->

# FastAPI People
<!-- stay:66Sz5jMc hash=sha256:4b46cddf0b79 -->

FastAPI has an amazing community that welcomes people from all backgrounds.
<!-- stay:NnhJ9exQ hash=sha256:d21dcc59fe5c -->

## Creator
<!-- stay:PF2gFG1Q hash=sha256:12fbdb027c5f -->

Hey! 👋
<!-- stay:aUluFeDx hash=sha256:bb7c08b3f737 -->

This is me:
<!-- stay:XYr4oncB hash=sha256:c82356ea7053 -->

<div class="user-list user-list-center">
{% for user in people.maintainers %}
<!-- stay:oElHjrbR hash=sha256:189b67ce0896 -->

<div class="user"><a href="{{ contributors.tiangolo.url }}"><div class="avatar-wrapper"><img src="{{ contributors.tiangolo.avatarUrl }}"/></div><div class="title">@{{ contributors.tiangolo.login }}</div></a> <div class="count">Answers: {{ user.answers }}</div><div class="count">Pull Requests: {{ contributors.tiangolo.count }}</div></div>
{% endfor %}
<!-- stay:7gvh7trF hash=sha256:70b5c7f1e9a4 -->

</div>
<!-- stay:Ylkejb5D hash=sha256:aac32651b10f -->

I'm the creator of **FastAPI**. You can read more about that in [Help FastAPI - Follow the author](help-fastapi.md#follow-the-author).
<!-- stay:xSL0IVzf hash=sha256:da83d8eb25b1 -->

...But here I want to show you the community.
<!-- stay:z8n5H612 hash=sha256:78a21f6838da -->

---
<!-- stay:9pUDy8oC hash=sha256:cb3f91d54eee -->

**FastAPI** receives a lot of support from the community. And I want to highlight their contributions.
<!-- stay:RtRsn4Jw hash=sha256:2076b290966e -->

These are the people that:
<!-- stay:K1Oyqip4 hash=sha256:be06bec39f02 -->

* [Help others with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github).
* Create or review Pull Requests.
* Help [manage the repository](https://tiangolo.com/open-source/management-tasks/) (team members).
<!-- stay:8iwmpugt hash=sha256:e54b6a2bccf7 -->

All these tasks help maintain the repository.
<!-- stay:6TqY511O hash=sha256:18c27a6b0ada -->

A round of applause to them. 👏 🙇
<!-- stay:byA7dKVy hash=sha256:82a575107aeb -->

## Team
<!-- stay:OfbxUWcv hash=sha256:53f40995fe65 -->

This is the current list of team members. 😎
<!-- stay:SAPrG6mF hash=sha256:34ca05e36110 -->

They have different levels of involvement and permissions, they can perform [repository management tasks](https://tiangolo.com/open-source/management-tasks/) and together we [manage the FastAPI repository](./management.md).
<!-- stay:8zM22Q1E hash=sha256:618eb726ac62 -->

<div class="user-list user-list-center">
<!-- stay:HxDKukIw hash=sha256:0ac6168a429f -->

{% for user in members["members"] %}
<!-- stay:CFo4fPyi hash=sha256:40cee4e9cc71 -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatar_url }}"/></div><div class="title">@{{ user.login }}</div></a></div>
<!-- stay:eaZHQHJe hash=sha256:49d687ddb525 -->

{% endfor %}
<!-- stay:sd4JoPqa hash=sha256:87a707183653 -->

</div>
<!-- stay:WcpT7GaB hash=sha256:aac32651b10f -->

Although the team members have the permissions to perform privileged tasks, all the help from others maintaining FastAPI is very much appreciated! 🙇‍♂️
<!-- stay:rm7Bw1Ut hash=sha256:28ea266f765c -->

## FastAPI Experts
<!-- stay:Nsyglv7d hash=sha256:2fa6b397399a -->

These are the users that have been [helping others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github). 🙇
<!-- stay:94wY1VgF hash=sha256:fe1718bb83e9 -->

They have proven to be **FastAPI Experts** by helping many others. ✨
<!-- stay:LCYtxrK1 hash=sha256:a9b4ba2e24ad -->

/// tip
<!-- stay:UAeqQUyw hash=sha256:35fc886a93b5 -->

You could become an official FastAPI Expert too!
<!-- stay:Q1Lzqqez hash=sha256:f160e1e2c68f -->

Just [help others with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github). 🤓
<!-- stay:giLTQRVs hash=sha256:9f0434e8d934 -->

///
<!-- stay:t0Mwh3IA hash=sha256:732c4e971163 -->

You can see the **FastAPI Experts** for:
<!-- stay:lGtQWyn6 hash=sha256:b0eec5d5f680 -->

* [Last Month](#fastapi-experts-last-month) 🤓
* [3 Months](#fastapi-experts-3-months) 😎
* [6 Months](#fastapi-experts-6-months) 🧐
* [1 Year](#fastapi-experts-1-year) 🧑‍🔬
* [**All Time**](#fastapi-experts-all-time) 🧙
<!-- stay:DMjNlSq0 hash=sha256:25f053e9180a -->

### FastAPI Experts - Last Month
<!-- stay:FPnmEFlQ hash=sha256:e8a1a7a40f8c -->

These are the users that have been [helping others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github) during the last month. 🤓
<!-- stay:SNUls2He hash=sha256:bbfaeb5a66cf -->

<div class="user-list user-list-center">
<!-- stay:m8Lcgh1R hash=sha256:0ac6168a429f -->

{% for user in people.last_month_experts[:10] %}
<!-- stay:r67a0HlD hash=sha256:6e1957ca9367 -->

{% if user.login not in skip_users %}
<!-- stay:yYJa1K8k hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Questions replied: {{ user.count }}</div></div>
<!-- stay:3mV2zS20 hash=sha256:98b8697bc29e -->

{% endif %}
<!-- stay:3suKslyE hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:DNvZTa6d hash=sha256:87a707183653 -->

</div>
<!-- stay:YSvEANrG hash=sha256:aac32651b10f -->

### FastAPI Experts - 3 Months
<!-- stay:TfzSLItH hash=sha256:5422b0f1c206 -->

These are the users that have been [helping others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github) during the last 3 months. 😎
<!-- stay:ywx54J6C hash=sha256:8d282b810f27 -->

<div class="user-list user-list-center">
<!-- stay:9babK4kc hash=sha256:0ac6168a429f -->

{% for user in people.three_months_experts[:10] %}
<!-- stay:H2cqBGJI hash=sha256:6dbaa5037a04 -->

{% if user.login not in skip_users %}
<!-- stay:cAyYfRbP hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Questions replied: {{ user.count }}</div></div>
<!-- stay:YxarSQv8 hash=sha256:98b8697bc29e -->

{% endif %}
<!-- stay:qYjjQsXP hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:sp4eWMu0 hash=sha256:87a707183653 -->

</div>
<!-- stay:JWQgm9lj hash=sha256:aac32651b10f -->

### FastAPI Experts - 6 Months
<!-- stay:A4hv73RD hash=sha256:fb041b17d6d8 -->

These are the users that have been [helping others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github) during the last 6 months. 🧐
<!-- stay:Go7JxG07 hash=sha256:9d3b8f0b72d5 -->

<div class="user-list user-list-center">
<!-- stay:r8IYQLhu hash=sha256:0ac6168a429f -->

{% for user in people.six_months_experts[:10] %}
<!-- stay:aSLI17UY hash=sha256:f29174a8b121 -->

{% if user.login not in skip_users %}
<!-- stay:BrRBKCft hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Questions replied: {{ user.count }}</div></div>
<!-- stay:X04zRkeA hash=sha256:98b8697bc29e -->

{% endif %}
<!-- stay:MtINhxX4 hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:riqMuzjy hash=sha256:87a707183653 -->

</div>
<!-- stay:DrKOAesm hash=sha256:aac32651b10f -->

### FastAPI Experts - 1 Year
<!-- stay:pAIUS2NN hash=sha256:2afab4520cd9 -->

These are the users that have been [helping others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github) during the last year. 🧑‍🔬
<!-- stay:Q6KRogGJ hash=sha256:497340a174e9 -->

<div class="user-list user-list-center">
<!-- stay:LKWa5ypD hash=sha256:0ac6168a429f -->

{% for user in people.one_year_experts[:20] %}
<!-- stay:5gKsMw1Q hash=sha256:8ce39a57147a -->

{% if user.login not in skip_users %}
<!-- stay:FhOUjH9r hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Questions replied: {{ user.count }}</div></div>
<!-- stay:gCWV0L1q hash=sha256:98b8697bc29e -->

{% endif %}
<!-- stay:OpJ2iuBh hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:fuOr3Mk4 hash=sha256:87a707183653 -->

</div>
<!-- stay:Jt3OW4mN hash=sha256:aac32651b10f -->

### FastAPI Experts - All Time
<!-- stay:xCFHLSTI hash=sha256:53b2ab61b314 -->

Here are the all time **FastAPI Experts**. 🤓🤯
<!-- stay:9gWQ6Gqq hash=sha256:11148d422a80 -->

These are the users that have [helped others the most with questions in GitHub](help-fastapi.md#help-others-with-questions-in-github) through *all time*. 🧙
<!-- stay:PU7lsE8t hash=sha256:9b5d87d2b392 -->

<div class="user-list user-list-center">
<!-- stay:oBKFvdqg hash=sha256:0ac6168a429f -->

{% for user in people.experts[:50] %}
<!-- stay:HfgiVOUt hash=sha256:8597ed99eb48 -->

{% if user.login not in skip_users %}
<!-- stay:z31AxZZt hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Questions replied: {{ user.count }}</div></div>
<!-- stay:p2Yp9zvb hash=sha256:98b8697bc29e -->

{% endif %}
<!-- stay:sAa3ByXo hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:iF6KtfLt hash=sha256:87a707183653 -->

</div>
<!-- stay:BHoEmSMt hash=sha256:aac32651b10f -->

## Top Contributors
<!-- stay:2JFeJ5hl hash=sha256:9b35f4696a56 -->

Here are the **Top Contributors**. 👷
<!-- stay:uriiRH6M hash=sha256:852b2ba8530c -->

These users have created the most Pull Requests that have been *merged*.
<!-- stay:tNPfwq3C hash=sha256:5bd35b4fb128 -->

They have contributed source code, documentation, etc. 📦
<!-- stay:dy8JMHF9 hash=sha256:cbb8ff7badf8 -->

<div class="user-list user-list-center">
<!-- stay:Sc08TS3E hash=sha256:0ac6168a429f -->

{% for user in (contributors.values() | list)[:50] %}
<!-- stay:dbJZeFhG hash=sha256:da2940ae5aa0 -->

{% if user.login not in skip_users %}
<!-- stay:5OXM8d0G hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Pull Requests: {{ user.count }}</div></div>
<!-- stay:8knssnrR hash=sha256:ef157450e584 -->

{% endif %}
<!-- stay:SJFJ8scv hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:w7fdgwOd hash=sha256:87a707183653 -->

</div>
<!-- stay:zpoEEh3h hash=sha256:aac32651b10f -->

There are hundreds of other contributors, you can see them all in the [FastAPI GitHub Contributors page](https://github.com/fastapi/fastapi/graphs/contributors). 👷
<!-- stay:Es7Cgf53 hash=sha256:15631995f68c -->

## Top Translation Reviewers
<!-- stay:5qgEE2Mq hash=sha256:2f26df4b72c7 -->

These users are the **Top Translation Reviewers**. 🕵️
<!-- stay:ispoRhis hash=sha256:370afc0f0739 -->

Translation reviewers have the **power to approve translations** of the documentation. Without them, there wouldn't be documentation in several other languages.
<!-- stay:MIUyJteE hash=sha256:5d182542d76b -->

<div class="user-list user-list-center">
{% for user in (translation_reviewers.values() | list)[:50] %}
<!-- stay:4LVLTu8y hash=sha256:41bbb589e08d -->

{% if user.login not in skip_users %}
<!-- stay:76MEtWYg hash=sha256:3b9b20e26e9e -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a> <div class="count">Reviews: {{ user.count }}</div></div>
<!-- stay:Dc4oC3kR hash=sha256:9b75f3fb50fa -->

{% endif %}
<!-- stay:L9lZQ3HI hash=sha256:3911e559d471 -->

{% endfor %}
<!-- stay:lvWSl6aI hash=sha256:87a707183653 -->

</div>
<!-- stay:RwzIcKjF hash=sha256:aac32651b10f -->

## Sponsors
<!-- stay:s226Jf79 hash=sha256:6dbc5a9aa091 -->

These are the **Sponsors**. 😎
<!-- stay:1CD9UhyS hash=sha256:c29bcc422001 -->

They are supporting my work with **FastAPI** (and others), mainly through [GitHub Sponsors](https://github.com/sponsors/tiangolo).
<!-- stay:MZx3O8zB hash=sha256:8964d8c69205 -->

{% if sponsors %}
<!-- stay:ugklaisT hash=sha256:9d94bed888bb -->

{% if sponsors.gold %}
<!-- stay:yIX4JrWR hash=sha256:48263ddf2aec -->

### Gold Sponsors
<!-- stay:UEGoDiZF hash=sha256:9044b5d34f7a -->

{% for sponsor in sponsors.gold -%}
<a href="{{ sponsor.url }}" title="{{ sponsor.title }}"><img src="{{ sponsor.img }}" style="border-radius:15px"></a>
{% endfor %}
{% endif %}
<!-- stay:7IIKkhvw hash=sha256:cefc434ae63c -->

{% if sponsors.silver %}
<!-- stay:ii5PAtbH hash=sha256:fa3c422c6619 -->

### Silver Sponsors
<!-- stay:h8xii77S hash=sha256:b6666198c380 -->

{% for sponsor in sponsors.silver -%}
<a href="{{ sponsor.url }}" title="{{ sponsor.title }}"><img src="{{ sponsor.img }}" style="border-radius:15px"></a>
{% endfor %}
{% endif %}
{% endif %}
<!-- stay:9D3BypOV hash=sha256:f3d5849f3643 -->

### Individual Sponsors
<!-- stay:HPUT6v2f hash=sha256:cc21ca159737 -->

{% if github_sponsors %}
{% for group in github_sponsors.sponsors %}
<!-- stay:5tg2p7OJ hash=sha256:95d24d282d2e -->

<div class="user-list user-list-center">
<!-- stay:ifHjKHbw hash=sha256:0ac6168a429f -->

{% for user in group %}
{% if user.login not in sponsors_badge.logins %}
<!-- stay:gexoX21i hash=sha256:a781daec9b97 -->

<div class="user"><a href="{{ user.url }}"><div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div><div class="title">@{{ user.login }}</div></a></div>
<!-- stay:LtamrUAJ hash=sha256:aa9f038b65f7 -->

{% endif %}
{% endfor %}
<!-- stay:YOfT5Ih5 hash=sha256:b75fa5b4936f -->

</div>
<!-- stay:1LUPxwi9 hash=sha256:aac32651b10f -->

{% endfor %}
{% endif %}
<!-- stay:Im3eoHIP hash=sha256:fc3fa564f65f -->

## About the data - technical details
<!-- stay:F5qzzsgz hash=sha256:e73a99e3eaff -->

The main intention of this page is to highlight the effort of the community to help others.
<!-- stay:z6NB2Zaa hash=sha256:ae36b42d9da9 -->

Especially including efforts that are normally less visible, and in many cases more arduous, like helping others with questions and reviewing Pull Requests with translations.
<!-- stay:WZ3wCKSW hash=sha256:97a9d211e47c -->

The data is calculated each month, you can read the [source code here](https://github.com/fastapi/fastapi/blob/master/scripts/).
<!-- stay:wBam1BUK hash=sha256:277dd4ad80ee -->

Here I'm also highlighting contributions from sponsors.
<!-- stay:rS90fBIa hash=sha256:af8cf2641080 -->

I also reserve the right to update the algorithm, sections, thresholds, etc (just in case 🤷).
<!-- stay:5S7p10DY hash=sha256:a32cd9512956 -->
