# python ./tools/img_effects.py

import os
from PIL import Image, ImageDraw, ImageEnhance
import numpy as np

class ImgEffects:

    def __init__(self, config):
        self.config = config
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.parent_dir = os.path.dirname(script_dir) + os.sep
        self.temp_dir = os.path.join(self.parent_dir, "_temp")
        os.makedirs(self.temp_dir, exist_ok=True)


    def preprocess_image(self, image_path, contrast=1.2, brightness=1.0, blur=False):
        """
        Prétraite l'image: conversion N&B, ajustements
        
        Args:
            image_path: Chemin de l'image source
            contrast: Facteur de contraste (1.0 = normal, >1 = plus de contraste)
            brightness: Facteur de luminosité (1.0 = normal)
            blur: Appliquer un léger flou pour lisser
        
        Returns:
            Image en niveaux de gris prétraitée
        """
        img = Image.open(image_path)
        
        # Convertir en niveaux de gris
        img_bw = img.convert('L')
        
        # Ajuster le contraste
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img_bw)
            img_bw = enhancer.enhance(contrast)
        
        # Ajuster la luminosité
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img_bw)
            img_bw = enhancer.enhance(brightness)
        
        # Flou optionnel
        if blur:
            from PIL import ImageFilter
            img_bw = img_bw.filter(ImageFilter.GaussianBlur(radius=1))
        
        return img_bw

    def apply_color_overlay(self, grayscale_img, overlay_color=None, opacity=0.5):
        """
        Applique un overlay coloré sur l'image en niveaux de gris
        
        Args:
            grayscale_img: Image en niveaux de gris
            overlay_color: Couleur de l'overlay (hex, rgb tuple, ou nom)
                        None = pas d'overlay, juste retourner l'image
            opacity: Opacité de l'overlay (0.0 = transparent, 1.0 = opaque)
        
        Returns:
            Image en niveaux de gris avec overlay appliqué
        """
        if overlay_color is None:
            return grayscale_img
        
        # Convertir la couleur en RGB
        def parse_color(color):
            if isinstance(color, str) and color.startswith('#'):
                # Convertir hex en RGB
                color = color.lstrip('#')
                return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
            elif isinstance(color, tuple):
                return color
            else:
                # Nom de couleur PIL - créer une image temporaire pour convertir
                temp = Image.new('RGB', (1, 1), color)
                return temp.getpixel((0, 0))
        
        rgb_color = parse_color(overlay_color)
        
        # Convertir l'image N&B en RGB pour appliquer l'overlay
        img_rgb = grayscale_img.convert('RGB')
        
        # Créer un calque de couleur
        overlay = Image.new('RGB', img_rgb.size, rgb_color)
        
        # Mélanger avec l'opacité spécifiée
        result = Image.blend(img_rgb, overlay, opacity)
        
        # Reconvertir en niveaux de gris pour préserver les valeurs
        return result.convert('L')


    def parse_color(self, color):
        """
        Utilitaire pour parser une couleur en format utilisable par PIL
        
        Args:
            color: Couleur (hex string, rgb tuple, ou nom)
        
        Returns:
            Couleur au format PIL
        """
        if isinstance(color, str) and color.startswith('#'):
            return color
        elif isinstance(color, tuple):
            return color
        else:
            return color  # Nom de couleur PIL


    # ========== ÉTAPE 3: CRÉATION DE LA TRAME ==========

    def create_halftone(self, grayscale_img, bg_color='white', dot_color='black', 
                    dot_size=5, scale=2, max_dot_size=0.95):
        """
        Crée l'effet tramé à partir d'une image en niveaux de gris
        
        Args:
            grayscale_img: Image PIL en niveaux de gris
            bg_color: Couleur de fond
            dot_color: Couleur des points
            dot_size: Taille de la grille (plus petit = plus de détails)
            scale: Facteur d'agrandissement de l'image finale
            max_dot_size: Taille max des points (0-1, 0.95 = 95% de la cellule)
        
        Returns:
            Image PIL avec effet tramé
        """
        img_width, img_height = grayscale_img.size
        
        # Créer l'image de sortie
        output_img = Image.new('RGB', 
                            (img_width * scale, img_height * scale), 
                            color=bg_color)
        draw = ImageDraw.Draw(output_img)
        
        # Parcourir l'image par grille
        for y in range(0, img_height, dot_size):
            for x in range(0, img_width, dot_size):
                # Extraire la région
                box = (x, y, 
                    min(x + dot_size, img_width), 
                    min(y + dot_size, img_height))
                region = grayscale_img.crop(box)
                
                # Luminosité moyenne (0=noir, 255=blanc)
                avg_brightness = np.array(region).mean()
                
                # Calculer le rayon (zones sombres = gros points)
                darkness = 1 - (avg_brightness / 255)
                radius = (dot_size * scale / 2) * darkness * max_dot_size
                
                # Dessiner le point
                if radius > 0.5:
                    center_x = (x + dot_size/2) * scale
                    center_y = (y + dot_size/2) * scale
                    draw.ellipse([center_x - radius, center_y - radius,
                                center_x + radius, center_y + radius],
                            fill=dot_color)
        
        return output_img


# ========== ÉTAPE 4: POST-TRAITEMENT ONDULATION ==========

    def apply_wave_distortion(self, img, wave_type='radial', intensity=20, frequency=0.05):
        """
        Applique un effet d'ondulation à l'image
        
        Args:
            img: Image PIL à déformer
            wave_type: Type d'ondulation ('radial', 'horizontal', 'vertical', 'circular')
            intensity: Amplitude de l'ondulation en pixels
            frequency: Fréquence des vagues (plus petit = vagues plus larges)
        
        Returns:
            Image PIL avec effet d'ondulation
        """
        import math
        
        width, height = img.size
        distorted = Image.new(img.mode, (width, height), 'white' if img.mode == 'RGB' else 0)
        pixels_src = img.load()
        pixels_dst = distorted.load()
        
        center_x = width / 2
        center_y = height / 2
        
        for y in range(height):
            for x in range(width):
                # Calculer le décalage selon le type d'ondulation
                if wave_type == 'radial':
                    # Ondulation depuis le centre
                    dx = x - center_x
                    dy = y - center_y
                    distance = math.sqrt(dx*dx + dy*dy)
                    wave = math.sin(distance * frequency) * intensity
                    
                    # Déplacer le pixel radialement
                    if distance > 0:
                        offset_x = int(x + (dx / distance) * wave)
                        offset_y = int(y + (dy / distance) * wave)
                    else:
                        offset_x, offset_y = x, y
                        
                elif wave_type == 'horizontal':
                    # Ondulation horizontale
                    wave = math.sin(y * frequency) * intensity
                    offset_x = int(x + wave)
                    offset_y = y
                    
                elif wave_type == 'vertical':
                    # Ondulation verticale
                    wave = math.sin(x * frequency) * intensity
                    offset_x = x
                    offset_y = int(y + wave)
                    
                elif wave_type == 'circular':
                    # Ondulation circulaire
                    dx = x - center_x
                    dy = y - center_y
                    distance = math.sqrt(dx*dx + dy*dy)
                    angle = math.atan2(dy, dx)
                    wave = math.sin(distance * frequency + angle * 3) * intensity
                    
                    if distance > 0:
                        offset_x = int(x + math.cos(angle) * wave)
                        offset_y = int(y + math.sin(angle) * wave)
                    else:
                        offset_x, offset_y = x, y
                else:
                    offset_x, offset_y = x, y
                
                # Copier le pixel si dans les limites
                if 0 <= offset_x < width and 0 <= offset_y < height:
                    pixels_dst[x, y] = pixels_src[offset_x, offset_y]
        
        return distorted

    def image_to_halftone(self, image_path, output_path, 
                        bg_color='white', dot_color='black',
                        dot_size=5, scale=2,
                        contrast=1.2, brightness=1.0, blur=False,
                        overlay_color=None, overlay_opacity=0.3,
                        wave_effect=None, wave_intensity=20, wave_frequency=0.05):
        """
        Pipeline complet: prétraitement + overlay + tramage + ondulation
        
        Args:
            image_path: Chemin image source
            output_path: Chemin image résultat
            bg_color: Couleur fond (ex: 'white', '#f0f0f0', (240,240,240))
            dot_color: Couleur points (ex: 'black', '#1a1a3a', (26,26,58))
            dot_size: Taille grille (3-8 recommandé)
            scale: Agrandissement (1-3)
            contrast: Contraste du prétraitement (0.5-2.0)
            brightness: Luminosité du prétraitement (0.5-1.5)
            blur: Appliquer un flou de lissage
            overlay_color: Couleur de teinte à appliquer (None = pas d'overlay)
            overlay_opacity: Opacité de l'overlay (0.0-1.0)
            wave_effect: Type d'ondulation ('radial', 'horizontal', 'vertical', 'circular', None)
            wave_intensity: Amplitude de l'ondulation en pixels
            wave_frequency: Fréquence des vagues (0.01-0.2)
        """
        print("🔄 Prétraitement de l'image...")
        grayscale = self.preprocess_image(image_path, contrast, brightness, blur)
        
        print("🎨 Application de l'overlay coloré...")
        grayscale = self.apply_color_overlay(grayscale, overlay_color, overlay_opacity)
        
        print("⚫ Création de la trame...")
        bg = self.parse_color(bg_color)
        dot = self.parse_color(dot_color)
        result = self.create_halftone(grayscale, bg, dot, dot_size, scale)
        
        # Appliquer l'ondulation si demandé
        if wave_effect:
            print(f"🌊 Application de l'ondulation {wave_effect}...")
            result = self.apply_wave_distortion(result, wave_effect, wave_intensity, wave_frequency)
        
        print(f"💾 Sauvegarde: {output_path}")
        result.save(output_path, quality=95)
        print("✅ Terminé!")
        
        return result

    def image_to_halftone1(self, image_path, output_path, 
                        bg_color='white', dot_color='black',
                        dot_size=5, scale=2,
                        contrast=1.2, brightness=1.0, blur=False,
                        overlay_color=None, overlay_opacity=0.3):
        """
        Pipeline complet: prétraitement + overlay + tramage
        
        Args:
            image_path: Chemin image source
            output_path: Chemin image résultat
            bg_color: Couleur fond (ex: 'white', '#f0f0f0', (240,240,240))
            dot_color: Couleur points (ex: 'black', '#1a1a3a', (26,26,58))
            dot_size: Taille grille (3-8 recommandé)
            scale: Agrandissement (1-3)
            contrast: Contraste du prétraitement (0.5-2.0)
            brightness: Luminosité du prétraitement (0.5-1.5)
            blur: Appliquer un flou de lissage
            overlay_color: Couleur de teinte à appliquer (None = pas d'overlay)
            overlay_opacity: Opacité de l'overlay (0.0-1.0)
        """
        print("🔄 Prétraitement de l'image...")
        grayscale = self.preprocess_image(image_path, contrast, brightness, blur)
        
        print("🎨 Application de l'overlay coloré...")
        grayscale = self.apply_color_overlay(grayscale, overlay_color, overlay_opacity)
        
        print("⚫ Création de la trame...")
        bg = self.parse_color(bg_color)
        dot = self.parse_color(dot_color)
        result = self.create_halftone(grayscale, bg, dot, dot_size, scale)
        
        print(f"💾 Sauvegarde: {output_path}")
        result.save(output_path, quality=95)
        print("✅ Terminé!")
        
        return result




    def create_halftone_1(self, image_path, output_path, dot_size=5, scale=4):
        """
        Crée un effet tramé (halftone) à partir d'une image
        """
        # Charger et convertir en niveaux de gris
        img = Image.open(image_path).convert('L')
        img_width, img_height = img.size
        
        # Créer l'image de sortie (fond blanc)
        output_img = Image.new('RGB', 
                            (img_width * scale, img_height * scale), 
                            color='white')
        draw = ImageDraw.Draw(output_img)
        
        # Parcourir l'image par grille
        for y in range(0, img_height, dot_size):
            for x in range(0, img_width, dot_size):
                # Extraire la région
                box = (x, y, 
                    min(x + dot_size, img_width), 
                    min(y + dot_size, img_height))
                region = img.crop(box)
                
                # Calculer la luminosité moyenne (0=noir, 255=blanc)
                avg_brightness = np.array(region).mean()
                
                # Plus c'est sombre dans l'original, plus le point doit être GRAND et FONCÉ
                # Inverser : zones sombres (0) → gros points noirs
                darkness = 1 - (avg_brightness / 255)
                radius = (dot_size * scale / 2) * darkness * 0.95
                
                # Dessiner le point NOIR
                if radius > 0.5:
                    center_x = (x + dot_size/2) * scale
                    center_y = (y + dot_size/2) * scale
                    draw.ellipse([center_x - radius, center_y - radius,
                                center_x + radius, center_y + radius],
                            fill='#1a1a3a')  # Bleu foncé/noir
        
        output_img.save(output_path)
        print(f"✓ Image tramée créée : {output_path}")

    def halftone_simple(self, image_path, output_path, cell_size=4, size_factor=2, fill_color="black", format="PNG"):

        img = Image.open(image_path).convert('L')
        w, h = img.size
        
        size_factor = int(size_factor)
        output = Image.new('RGB', (w*size_factor, h*size_factor), 'white')
        draw = ImageDraw.Draw(output)
        
        for y in range(0, h, cell_size):
            for x in range(0, w, cell_size):
                # Région de pixels
                region = img.crop((x, y, 
                                min(x+cell_size, w), 
                                min(y+cell_size, h)))
                
                # Luminosité moyenne (0-255)
                brightness = np.array(region).mean()
                
                # Rayon du point (sombre = grand)
                radius = (cell_size * (255 - brightness) / 255) * 0.9
                
                if radius > 0.3:
                    cx = (x + cell_size/size_factor) * size_factor
                    cy = (y + cell_size/size_factor) * size_factor
                    draw.ellipse([cx-radius*size_factor, cy-radius*size_factor, 
                                cx+radius*size_factor, cy+radius*size_factor], 
                            fill=fill_color)
                    
        if format.upper() == 'WEBP':
            output_path = output_path + ".webp"
            print(output_path)
            output.save(output_path, format='WEBP', quality=95, method=6)
        else:  # PNG par défaut
            output.save(output_path +".png", format='PNG', optimize=True)
            
        # output.save(output_path, quality=95)



if __name__ == '__main__':
    # os.system('clear')
    import tools
    config = tools.site_yml('site.yml')
    img = ImgEffects(config)

    source = os.path.join(img.temp_dir,'test2.webp')
    target = os.path.join(img.temp_dir,'effect')

    img.halftone_simple(source, target, cell_size=2, size_factor=2, fill_color="black")
    exit()

    img.image_to_halftone(
        source,
        target,
        bg_color='#FFFFFF',
        dot_color='#4e3eb5',
        dot_size=6,
        scale=2,
        contrast=1.4,
        wave_effect='horizontal', #radial, circular, horizontal, vertical
        wave_intensity=5,
        wave_frequency=0.2
    )

    # img.create_halftone('macron.webp', 'image_tramee.png', dot_size=5, scale=2)
    # img.halftone_simple('macron.webp', 'image_tramee.png', cell_size=5)