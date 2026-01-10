# 🔄 Shopware → Odoo Export Tool

Application web pour exporter vos commandes Shopware et les préparer pour Odoo.

## 🚀 Déploiement en 3 étapes

### Étape 1 : Déployer l'API sur Vercel (5 min)

1. Créez un compte gratuit sur [vercel.com](https://vercel.com)

2. Installez Vercel CLI :
```bash
npm install -g vercel
```

3. Allez dans le dossier `vercel-api` :
```bash
cd vercel-api
```

4. Déployez :
```bash
vercel
```

5. Suivez les instructions (appuyez sur Entrée pour les valeurs par défaut)

6. **Notez l'URL** fournie (ex: `https://votre-app.vercel.app`)

---

### Étape 2 : Déployer l'interface sur GitHub Pages (2 min)

1. Créez un nouveau repository sur GitHub (ex: `shopware-odoo-export`)

2. Uploadez le contenu du dossier `github-pages` :
   - `index.html`

3. Allez dans **Settings → Pages**

4. Source : **Deploy from branch → main → / (root)**

5. Cliquez sur **Save**

6. Attendez 1-2 minutes, votre app sera disponible à :
   ```
   https://votre-username.github.io/shopware-odoo-export/
   ```

---

### Étape 3 : Configurer et utiliser (1 min)

1. Ouvrez votre app GitHub Pages

2. Entrez l'URL de votre API Vercel (étape 1)

3. Cliquez sur **Tester la connexion**

4. Choisissez le statut des commandes

5. Cliquez sur **Exporter** !

---

## ✨ Fonctionnalités

- ✅ Export des commandes Shopware
- ✅ Filtrage par statut (Open, En cours, Terminée, etc.)
- ✅ Génération Excel directement dans le navigateur
- ✅ Aperçu des données avant téléchargement
- ✅ Interface moderne et intuitive
- ✅ 100% gratuit (Vercel + GitHub Pages)
- ✅ Aucune installation nécessaire pour les utilisateurs

---

## 📱 Partage avec votre équipe

Une fois déployé, partagez simplement l'URL GitHub Pages :
```
https://votre-username.github.io/shopware-odoo-export/
```

Vos collègues peuvent l'utiliser immédiatement !

---

## 🔒 Sécurité

- L'API Vercel ne stocke aucune donnée
- Les credentials Shopware sont dans les variables d'environnement Vercel
- Toutes les communications sont en HTTPS

---

## 🆘 Support

En cas de problème :
1. Vérifiez que l'URL Vercel est correcte
2. Testez la connexion
3. Regardez la console du navigateur (F12)

---

## 📝 TODO (futures améliorations)

- [ ] Upload de la base articles Odoo pour mapping
- [ ] Export multi-statuts
- [ ] Filtres par date
- [ ] Import direct dans Odoo via API

---

Fait avec ❤️ pour faciliter la vie des équipes !
