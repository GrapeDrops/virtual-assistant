from __future__ import division
import re
from gtts import gTTS
from io import BytesIO
import pygame
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from google.oauth2 import service_account
import pyaudio
from six.moves import queue
from datetime import datetime, date
import calendar
import os
import webbrowser
import urllib.request
import urllib.parse
from googlesearch import search
from joke.jokes import icanhazdad

########################################################################################################################
#       There is a README.txt file that explains a requirement for running this program, please go read it first!      #
########################################################################################################################

# Audio recording parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1  # The API currently only supports 1-channel (mono) audio
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms
name = None


# Google audio streaming example taken from: https://cloud.google.com/speech-to-text/docs/streaming-recognize
# For best result, position microphone as close to the user as possible
class AudioStream(object):
    """
    Opens a recording stream as a generator yielding the audio chunks.
    """
    def __init__(self):
        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self.closed = False
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )
        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """
        Continuously collect data from the audio stream, into the buffer.
        """
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            data = [self._buff.get()]
            if data[0] is None:
                return

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


def command_listen(responses):
    """
    Iterates through server responses and prints them.
    The responses passed is a generator that will block until a response is provided by the server.
    Each response may contain multiple results, and each result may contain multiple alternatives; for details,
    see https://goo.gl/tjCPAU.  Here we print and execute only the transcription for the top alternative of the
    top result.
    """
    for r in responses:
        if not r.results:
            continue
        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        command = r.results[0]
        if not command.alternatives:
            continue

        # We only care about final results in order to process the commands
        if command.is_final:
            transcript = command.alternatives[0].transcript.lstrip()
            transcript = re.sub(r"what\'s", "what is", transcript)
            transcript = re.sub(r"that\'s", "that is", transcript)
            transcript = re.sub(r"n\'t", " not", transcript)
            print(transcript)

            # Exit program if command is exit or quit
            if transcript.lower() == 'exit' or transcript.lower() == 'quit':
                assistant_talk('Goodbye')
                break
            else:
                command_execution(transcript.lower())


def command_execution(transcript):
    """
    This function provides the behavior for the different commands.
    The available commands are:
        -"hi/thank you"
        -"what is your name?" for name checking
        -"your name is" for name setting
        -"that is/was not" if you are dissatisfied
        -"tell me a joke", quite self explanatory
        -"is this the real life" attempts to sing Bohemian Rhapsody
        -"What time is it?" for getting time
        -"What is the date? / What day is it?" to get date
        -"Play..." will play a .mp3 file if it exists in the directory, otherwise it will play first result on Youtube
        -"Open..." will open a website based on a Google search on that query
    """
    global name
    if 'your name is' in transcript:
        name = ' '.join(transcript.split()[3:])
        assistant_talk('Okay')
        return
    elif 'that is not ' in transcript or 'that was not ' in transcript:
        assistant_talk('I\'m sorry')
        return
    elif transcript == 'thank you':
        assistant_talk('You\'re welcome')
        return
    elif transcript == 'hi' or transcript == 'hello':
        assistant_talk('Hello')
        return
    elif transcript == 'tell me a joke':
        assistant_talk(icanhazdad())
        return
    elif transcript == 'is this the real life':
        assistant_talk('Is this just fantasy? Caught in a landslide, no escape from reality. '
                       'Open your eyes, look up to the skies and see.')
        return

    if transcript.split(' ', 1)[0] == 'what':
        command = ' '.join(transcript.split()[1:])
        if command == "is your name":
            if name is None:
                assistant_talk('I have no name')
            else:
                assistant_talk('My name is ' + name)
        elif re.search('time', transcript, re.IGNORECASE):
            assistant_talk('It is currently ' + str(datetime.now().time().replace(microsecond=0)))
        elif re.search('day|date', transcript, re.IGNORECASE):
            assistant_talk('Today is ' + str(calendar.day_name[date.today().weekday()]) + ' ' + str(date.today()))
        return
    elif transcript.split(' ', 1)[0] == 'play':
        command = ' '.join(transcript.split()[1:])
        try:
            os.startfile(command + '.mp3')
        except FileNotFoundError:
            query_string = urllib.parse.urlencode({"search_query": command})
            html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
            search_results = re.findall(r'href=\"\/watch\?v=(.{11})', html_content.read().decode())
            webbrowser.open("http://www.youtube.com/watch?v=" + search_results[0])
        return
    elif transcript.split(' ', 1)[0] == 'open':
        command = ' '.join(transcript.split()[1:])
        url_generator = search(command, num=1, stop=1)
        for url in url_generator:
            webbrowser.open(url)
        return


def assistant_talk(text):
    """
    This function takes the text to be voiced and prints + plays the sound.
    """
    print(text)
    f = BytesIO()
    tts = gTTS(text=text, lang='en')
    tts.write_to_fp(f)
    f.seek(0)
    pygame.mixer.music.load(f)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():  # We want the file to play out before closing
        continue
    f.close()


def main():
    # NOTE: change authentication_file for your own .json file provided by Google
    # Another option is to set the GOOGLE_APPLICATION_CREDENTIALS environment variable to this file.
    authentication_file = "google_credentials.json"
    credentials = service_account.Credentials.from_service_account_file(authentication_file)
    # Instantiates a client
    client = speech.SpeechClient(credentials=credentials)
    # Having speech contexts can improve accuracy for specific sentences, need to manually add vocab.
    # Uncomment below to use.
    # speech_contexts = [{"phrases": ['phrase 1', 'phrase 2', 'etc']}]
    config = types.RecognitionConfig(
        # speech_contexts=speech_contexts,
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code='en-US')  # See http://g.co/cloud/speech/docs/languages for a list of supported languages.
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        interim_results=False,  # We only care about final result
        single_utterance=False)

    pygame.mixer.init()
    assistant_talk('Fired up and ready to serve')
    with AudioStream() as s:
        audio_generator = s.generator()
        requests = (types.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)
        responses = client.streaming_recognize(streaming_config, requests)

        # Now, put the transcription responses to use.
        command_listen(responses)


if __name__ == '__main__':
    main()
