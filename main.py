import pygame
import os
from colorama import Fore, Back, Style, init

init(autoreset=True)

# Initialize the pygame mixer (for playing sounds)
pygame.mixer.init()

# Start playing the background music
try:
    pygame.mixer.music.load("song.mp3")
    pygame.mixer.music.play(-1)  # The -1 means to loop the song indefinitely
except pygame.error as e:
    print("Error loading or playing the music:", str(e))


class Game:
    def __init__(self, scenes):
        self.scenes = scenes
        self.current_scene = "start"
        self.username = ""

    def play(self):
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear the screen
        print(r"""
WELCOME TO MY TEXT-BASED ADVENTURE GAME BASED ON... 
        
           _____ __                _       __               
          / ___// /_____ ______   | |     / /___ ___________
          \__ \/ __/ __ `/ ___/   | | /| / / __ `/ ___/ ___/
         ___/ / /_/ /_/ / /       | |/ |/ / /_/ / /  (__  ) 
        /____/\__/\__,_/_/        |__/|__/\__,_/_/  /____/  
        
        """)
        self.get_username()
        while self.current_scene:
            scene = self.scenes[self.current_scene]
            self.current_scene = scene.enter(self)

    def change_scene(self, scene_name):
        if scene_name in self.scenes:
            self.current_scene = scene_name
        else:
            print("The game doesn't know this scene. Try again!")

    def get_username(self):
        self.username = input("Enter your name: ")


class Scene:
    def __init__(self, description, choices):
        self.description = description
        self.choices = choices

    def enter(self, game):
        color_dict = {'RED': Fore.RED, 'BLUE': Fore.BLUE, 'BRIGHT': Style.BRIGHT, 'RESET_ALL': Style.RESET_ALL, 'Style': Style}
        print("=" * 60)
        print(self.description.format_map({**vars(game), **color_dict}))
        print("-" * 60)
        if self.choices:
            print("Your options:")
            for i, choice in enumerate(self.choices, start=1):
                print(f"{i}. {choice.format_map({**vars(game), **color_dict})}")
            user_input = self.get_valid_input("Choose an option (enter the number): ", range(1, len(self.choices) + 1))
            return self.choices[list(self.choices.keys())[user_input - 1]]
        else:
            return None

    @staticmethod
    def get_valid_input(prompt, valid_choices):
        while True:
            try:
                user_input = int(input(prompt))
                if user_input in valid_choices:
                    return user_input
                else:
                    print("Invalid option. Try again.")
            except ValueError:
                print("Invalid input. Enter a number.")


scenes = {
    "start": Scene(
        description="Welcome, {username}. Would you like to play as {RED}{Style.BRIGHT}Anakin Skywalker{Style.RESET_ALL} or {BLUE}{Style.BRIGHT}Obi-Wan Kenobi{Style.RESET_ALL}?",
        choices={
            "Play as {RED}{Style.BRIGHT}Anakin Skywalker{Style.RESET_ALL}": "anakin_start",
            "Play as {BLUE}{Style.BRIGHT}Obi-Wan Kenobi{Style.RESET_ALL}": "obiwan_start",
        }
    ),
    "anakin_start": Scene(
        description="You are {RED}{Style.BRIGHT}Anakin Skywalker{Style.RESET_ALL}, standing on the fiery planet of Mustafar. You have just choked Padmé and she lies unconscious. {BLUE}{Style.BRIGHT}Obi-Wan Kenobi{Style.RESET_ALL} confronts you, demanding, 'Let her go, Anakin.'",
        choices={
            "Accuse Obi-Wan: 'What have you and she been up to?'": "anakin_accuse",
            "Prepare for battle: 'You will not take her from me.'": "anakin_prepare_battle",
        }
    ),
    "anakin_accuse": Scene(
        description="You accuse Obi-Wan and Padmé of betrayal. Obi-Wan denies it and says, 'You have done that yourself.'",
        choices={
            "Insist: 'You turned her against me.'": "anakin_insist",
            "Prepare for battle: 'You will not take her from me.'": "anakin_prepare_battle",
        }
    ),
    "anakin_insist": Scene(
        description="You insist that Obi-Wan turned Padmé against you. Obi-Wan tries to reason with you, but you're not listening. You say, 'You will not take her from me.'",
        choices={
            "Throw off your cloak and prepare for battle": "anakin_prepare_battle",
        }
    ),
    "anakin_prepare_battle": Scene(
        description="You throw off your cloak and prepare for battle. Obi-Wan says, 'Your anger and your lust for power have already done that. You have allowed this Dark Lord to twist your mind until now . . . until now you have become the very thing you swore to destroy.'",
        choices={
            "Challenge Obi-Wan: 'Don't lecture me, Obi-Wan. I see through the lies of the Jedi. I do not fear the dark side as you do. I have brought peace, justice, freedom, and security to my new Empire.'": "anakin_challenge",
        }
    ),
    "anakin_challenge": Scene(
        description="You challenge Obi-Wan, declaring your new allegiance to your 'new Empire'. Obi-Wan responds, 'Your new Empire? Anakin, my allegiance is to the Republic ... to democracy.'",
        choices={
            "Ultimatum to Obi-Wan: 'If you're not with me, you're my enemy.'": "anakin_ultimatum",
        }
    ),
    "anakin_ultimatum": Scene(
        description="You give Obi-Wan an ultimatum. He responds, 'Only a Sith Lord deals in absolutes. I will do what I must.' You ignite your lightsaber and say, 'You will try.'",
        choices={
            "Begin the fight": "anakin_battle_1",
        }
    ),
    "anakin_battle_1": Scene(
        description="The battle begins. You and Obi-Wan are evenly matched, your lightsabers clashing in a deadly dance. You say, 'Don't make me destroy you, Master. You're no match for the dark side.'",
        choices={
            "Continue the fight": "anakin_battle_2",
        }
    ),
    "anakin_battle_2": Scene(
        description="The fight continues, with you pushing Obi-Wan back. Obi-Wan says, 'I've heard that before, Anakin . . . but I never thought I'd hear it from you.'",
        choices={
            "Continue the fight": "anakin_battle_3",
        }
    ),
    "anakin_battle_3": Scene(
        description="The battle rages on, moving from the control room to the balcony. You force Obi-Wan down a narrow balcony, ripping objects off the wall and throwing them at him. You say, 'You hesitate . . . the flaw of compassion.'",
        choices={
            "Continue the fight": "anakin_battle_4",
        }
    ),
    "anakin_battle_4": Scene(
        description="The fight continues along the lava river, with you and Obi-Wan jumping from platform to platform. You say, 'I should have known the Jedi were plotting to take over.'",
        choices={
            "Continue the fight": "anakin_battle_5",
        }
    ),
    "anakin_battle_5": Scene(
        description="The battle rages on. You push Obi-Wan back, your lightsabers clashing in a deadly dance. You say, 'From the Jedi point of view! From my point of view, the Jedi are evil.' Obi-Wan responds, 'Well, then you are lost!'",
        choices={
            "Continue the fight": "anakin_battle_6",
        }
    ),
    "anakin_battle_6": Scene(
        description="The fight continues until Obi-Wan jumps toward the safety of the black sandy edge of the lava river. He yells at you, 'It's over, Anakin. I have the high ground.'",
        choices={
            "Defy Obi-Wan: 'You underestimate my power!'": "anakin_defy",
        }
    ),
    "anakin_defy": Scene(
        description="You defy Obi-Wan, leaping to attack him despite his advantage. Obi-Wan severs your legs and arm with a swift strike. You tumble down the embankment and roll to a stop near the edge of the lava. Your clothes catch fire. Obi-Wan looks down at you, grief in his eyes. 'You were the Chosen One! It was said that you would destroy the Sith, not join them. You were to bring balance to the Force, not leave it in Darkness.' He picks up your lightsaber and begins to walk away. You scream after him, 'I hate you!' He stops, looking back. 'You were my brother, Anakin. I loved you.'",
        choices=None,
    ),
    "obiwan_start": Scene(
        description="You are {BLUE}{Style.BRIGHT}Obi-Wan Kenobi{Style.RESET_ALL}, standing on the fiery planet of Mustafar. You confront {RED}{Style.BRIGHT}Anakin Skywalker{Style.RESET_ALL}, trying to bring him back to the light side. You demand, 'Let her go, Anakin.'",
        choices={
            "Accuse Anakin: 'Your anger and your lust for power have already done that.'": "obiwan_accuse",
            "Prepare for battle: 'I will do what I must.'": "obiwan_prepare_battle",
        }
    ),
    "obiwan_accuse": Scene(
        description="You accuse Anakin of letting his anger and lust for power cloud his judgement. Anakin doesn't seem to take your words to heart. You say, 'You have allowed this Dark Lord to twist your mind until now . . . until now you have become the very thing you swore to destroy.'",
        choices={
            "Challenge Anakin: 'Anakin, my allegiance is to the Republic ... to democracy.'": "obiwan_challenge",
            "Prepare for battle: 'I will do what I must.'": "obiwan_prepare_battle",
        }
    ),
    "obiwan_challenge": Scene(
        description="You challenge Anakin, declaring your allegiance to the Republic and democracy. Anakin responds, 'If you're not with me, you're my enemy.' You reply, 'Only a Sith Lord deals in absolutes. I will do what I must.'",
        choices={
            "Ignite your lightsaber and attack": "obiwan_battle_1",
        }
    ),
    "obiwan_prepare_battle": Scene(
        description="You throw off your cloak and prepare for battle. Anakin challenges you, 'Don't make me kill you.'",
        choices={
            "Ignite your lightsaber and attack": "obiwan_battle_1",
        }
    ),
    "obiwan_battle_1": Scene(
        description="The battle begins. You and Anakin are evenly matched, your lightsabers clashing in a deadly dance. You say, 'Anakin, Chancellor Palpatine is evil.'",
        choices={
            "Continue the fight": "obiwan_battle_2",
        }
    ),
    "obiwan_battle_2": Scene(
        description="The fight continues, with Anakin pushing you back. You say, 'From the Sith!!! Anakin, Chancellor Palpatine is evil.' Anakin replies, 'From the Jedi point of view! From my point of view, the Jedi are evil.'",
        choices={
            "Continue the fight": "obiwan_battle_3",
        }
    ),
    "obiwan_battle_3": Scene(
        description="The fight rages on, moving from the control room to the balcony. Anakin forces you down a narrow balcony, ripping objects off the wall and throwing them at you. Anakin says, 'You hesitate . . . the flaw of compassion.'",
        choices={
            "Continue the fight": "obiwan_battle_4",
        }
    ),
    "obiwan_battle_4": Scene(
        description="The fight continues along the lava river, with you and Anakin jumping from platform to platform. You say, 'I have failed you, Anakin. I was never able to teach you to think.'",
        choices={
            "Continue the fight": "obiwan_battle_5",
        }
    ),
    "obiwan_battle_5": Scene(
        description="The battle rages on. You push Anakin back, your lightsabers clashing in a deadly dance. You say, 'Well, then you are lost!'",
        choices={
            "Continue the fight": "obiwan_battle_6",
        }
    ),
    "obiwan_battle_6": Scene(
        description="The fight continues until you jump toward the safety of the black sandy edge of the lava river. You yell at Anakin, 'It's over, Anakin. I have the high ground.'",
        choices={
            "Warn Anakin: 'Don't try it.'": "obiwan_warn",
        }
    ),
    "obiwan_warn": Scene(
        description="You warn Anakin not to attack, but he does it anyway. You sever his legs and arm with a swift strike. He tumbles down the embankment and rolls to a stop near the edge of the lava. His clothes catch fire. You look down at him, grief in your eyes. 'You were the Chosen One! It was said that you would destroy the Sith, not join them. You were to bring balance to the Force, not leave it in Darkness.' You pick up Anakin's lightsaber and begin to walk away. He screams after you, 'I hate you!' You stop, looking back. 'You were my brother, Anakin. I loved you.'",
        choices=None,
    ),
}

game = Game(scenes)
game.play()
