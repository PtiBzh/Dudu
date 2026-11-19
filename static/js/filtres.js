/* Dudu — filtres vivants (liste des postes, liste des actions, carte).
 *
 * Les listes déroulantes et cases à cocher relancent la page dès
 * qu'elles changent ; la recherche texte attend une micro-pause
 * (300 ms) après la dernière frappe pour ne pas recharger à chaque
 * lettre. Le bouton « Filtrer » disparaît.
 */
"use strict";

document.addEventListener("DOMContentLoaded", function () {
  var formulaire = document.querySelector("form.filtres");
  if (formulaire === null) return;

  /* Après un rechargement déclenché par la frappe, le curseur
   * revient à la fin du mot recherché : on enchaîne les touches. */
  var champTexte = formulaire.querySelector("input[type='text']");
  if (champTexte !== null && champTexte.value !== "") {
    champTexte.focus();
    champTexte.setSelectionRange(
      champTexte.value.length,
      champTexte.value.length
    );
  }

  function relancer() {
    formulaire.submit();
  }

  /* Un choix dans une liste déroulante ou une case cochée : la
   * page repart tout de suite. */
  formulaire.addEventListener("change", function (evenement) {
    var cible = evenement.target;
    if (cible.matches("select, input[type='checkbox']")) relancer();
  });

  /* Recherche texte : micro-pause de 300 ms après la dernière
   * frappe, relancée à chaque nouvelle lettre. */
  var minuteur = null;
  formulaire.addEventListener("input", function (evenement) {
    if (evenement.target !== champTexte) return;
    if (minuteur !== null) window.clearTimeout(minuteur);
    minuteur = window.setTimeout(relancer, 300);
  });
});
