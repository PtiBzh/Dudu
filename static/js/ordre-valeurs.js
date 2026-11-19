/* Dudu — réordonnancement des listes de valeurs par glisser-déposer
 * (Paramètres). Les lignes ne deviennent déplaçables que depuis la
 * poignée : les champs texte de la ligne restent éditables et
 * sélectionnables normalement.
 *
 * À la pose, les identifiants sont sérialisés dans l'ordre affiché
 * et le formulaire caché de la carte est envoyé : le serveur réécrit
 * les rangs 1..n. Sans JS, les lignes restent lisibles, l'ordre se
 * règle à la main via les formulaires d'édition.
 */
"use strict";

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".carte-param").forEach(function (carte) {
    var liste = carte.querySelector(".liste-valeurs");
    var forme = carte.querySelector(".forme-ordre .ordre-serialise");
    if (!liste || !forme) return;

    /* La poignée arme le glissement de sa ligne, rien d'autre :
     * le champ texte garde sa sélection, son curseur, son copier. */
    liste.addEventListener("mousedown", function (e) {
      var poignee = e.target.closest(".poignee-glisser");
      if (!poignee) return;
      e.preventDefault();
      poignee.closest(".ligne-valeur").setAttribute("draggable", "true");
    });
    document.addEventListener("mouseup", function () {
      liste.querySelectorAll("[draggable]").forEach(function (ligne) {
        ligne.removeAttribute("draggable");
      });
    });

    liste.addEventListener("dragstart", function (e) {
      var ligne = e.target.closest(".ligne-valeur");
      if (!ligne || ligne.getAttribute("draggable") !== "true") {
        e.preventDefault();
        return;
      }
      e.dataTransfer.setData("text/plain", ligne.dataset.pk);
      e.dataTransfer.effectAllowed = "move";
      ligne.classList.add("en-glissee");
    });

    liste.addEventListener("dragend", function (e) {
      var ligne = e.target.closest(".ligne-valeur");
      if (!ligne) return;
      ligne.classList.remove("en-glissee");
      ligne.removeAttribute("draggable");
    });

    liste.addEventListener("dragover", function (e) {
      var cible = e.target.closest(".ligne-valeur");
      var glissee = liste.querySelector(".en-glissee");
      if (!cible || !glissee || glissee === cible) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      var rect = cible.getBoundingClientRect();
      var apres = e.clientY - rect.top > rect.height / 2;
      cible.parentNode.insertBefore(
        glissee,
        apres ? cible.nextSibling : cible
      );
    });

    liste.addEventListener("drop", function (e) {
      if (!liste.querySelector(".en-glissee")) return;
      e.preventDefault();
      forme.value = Array.prototype.map
        .call(liste.querySelectorAll(".ligne-valeur"), function (ligne) {
          return ligne.dataset.pk;
        })
        .join(",");
      forme.form.submit();
    });
  });
});
