# virtual-assistant
## Speech to text
Speech to text is done through the Google Cloud API, requiring an active internet connection. While the most common implementation consists of recording a voice file and sending it to
Google’s servers, I did not want to waste OS resources saving and deleting/overwriting those temporary voice files, and thus settled on directly streaming the audio in chunks, per Google’s recommended recording parameters, found here:
https://cloud.google.com/speech-to-text/docs/best-practices

## Text to speech
Text to speech follows a similar direction by using Google’s services. However, this is done through the gTTS library, which is an interface to the Google Translate API. The limitation of this approach is the lack of voice diversity, where the English language only has the default monotone female voice. This was used to give voiced feedback to the user. Following the previous idea of not wanting to save and delete an audio file, I instead create a file-like object in memory with the io library to temporarily store the received audio and play it through the pygame library.

## User command execution
This part was done in a very simplistic manner, where just a few conditionals were used to check commands and execute them. These commands could just be for conversation, or automatically opening a file in the directory, or perhaps a website. While it works alright for this kind of limited functionality, I would look to take a more efficient approach to identify the commands to be more scalable.

## Notes
In order to use Google Cloud, an account is necessary. This will link the project to your account.
In order to run the program, you may create a free account and introduce your own credentials.
You may find the steps to do so here:
https://cloud.google.com/speech-to-text/docs/quickstart-client-libraries

Each audio stream session has a time limit. In my case, this limit was of 305 seconds, after which
the program would exit with an exception. It is possible to keep the program running after the
time limit, by encapsulating the streaming request-response loop in a try-catch block, resetting
the connection when the exception is met. Do note however that if the exception is set too broad,
it could influence the program’s other exception values, such as not allowing the program to quit
with exit code 0 following the ‘quit’ or ‘exit’ command.  
Should the accuracy of the program prove insufficient by the user, it is possible to set specific
phrases that the service will be more likely to respond with. This is done through the
speech_contexts field of the request configuration.

## Requirements
Requirements ( generated through pipreqs) [ pip install pipreqs ]:  
google==2.0.3  
six==1.12.0  
pygame==1.9.6  
axju_jokes==1.0.3  
PyAudio==0.2.11  
gTTS==2.0.4  
protobuf==3.11.1  
