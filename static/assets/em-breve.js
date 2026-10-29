  // Conteúdo específico por módulo
  (function () {
    var mods = {
      cursos:      { name: 'Cursos recomendados', title: 'Cursos recomendados', lead: 'Cursos externos de programação e matemática que fazem sentido começar logo no início da graduação.', body: '<p>Estamos construindo uma lista de cursos externos que ajudam calouros a se prepararem para as disciplinas iniciais de programação e matemática do curso. Cada indicação será acompanhada de uma breve justificativa de veteranos.</p>' },
      vagas:       { name: 'Vagas de estágio', title: 'Vagas de estágio', lead: 'Repositório centralizado de vagas relevantes para alunos com a graduação em andamento.', body: '<p>Este módulo reunirá vagas de estágio publicadas por empresas parceiras, alunos ou docentes, organizadas por área e por semestre recomendado. O objetivo é reduzir a dispersão de oportunidades entre canais informais.</p>' },
      ic:          { name: 'Projetos de IC', title: 'Projetos de Iniciação Científica', lead: 'Divulgação centralizada de projetos de IC oferecidos por professores da EACH-USP.', body: '<p>Reuniremos, em um único lugar, os projetos de Iniciação Científica em aberto, com informações sobre linhas de pesquisa, pré-requisitos e formas de contato com os responsáveis.</p>' },
      aex:         { name: 'Projetos de AEX', title: 'Projetos de AEX', lead: 'Atividades extensionistas para completar horas complementares e recompensar veteranos que contribuem.', body: '<p>Este módulo também funcionará como mecanismo de recompensa para veteranos que publicam material na plataforma, por meio da abertura de projetos de extensão em parceria com professores.</p>' },
      dicas:       { name: 'Dicas', title: 'Dicas de veteranos', lead: 'Orientações gerais sobre a vida acadêmica na EACH-USP.', body: '<p>Reuniremos orientações práticas sobre como fazer requerimentos, como organizar a rotina de estudo na universidade e como ingressar em um projeto de pesquisa ao longo do curso.</p>' },
      intercambio: { name: 'Intercâmbio', title: 'Intercâmbio', lead: 'Informações e relatos sobre programas de intercâmbio.', body: '<p>Este módulo concentrará informações sobre editais, requisitos, prazos e relatos de alunos que já participaram de programas de intercâmbio pela USP.</p>' },
      carreiras:   { name: 'Possíveis carreiras', title: 'Possíveis carreiras', lead: 'Trajetórias de carreira possíveis a partir de Sistemas de Informação.', body: '<p>Apresentaremos as principais trajetórias de carreira a partir do curso, com informações sobre competências, empresas e formas de se direcionar em cada uma delas.</p>' },
      entidades:   { name: 'Entidades', title: 'Entidades', lead: 'Informações sobre entidades estudantis da EACH-USP.', body: '<p>Este módulo reunirá informações sobre entidades estudantis da EACH-USP, com detalhes sobre o que são e como participar.</p>' }
    };

    var key = new URLSearchParams(location.search).get('m');
    var data = mods[key];
    if (!data) return;

    document.title = data.name + ' — Trilha USP';
    document.getElementById('crumb-name').textContent = data.name;
    document.getElementById('page-title').textContent = data.title;
    document.getElementById('page-lead').textContent = data.lead;
    document.getElementById('sec-body').innerHTML = data.body;
  })();
