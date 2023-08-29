from characterai import PyCAI

class ChatSession:
    def __init__(self, api_key: str, character_id: str) -> None:
        self.client = PyCAI(api_key)
        self.client.start()
        self.character_id = character_id
        self.chat = self.client.chat.new_chat(character_id)
    
    def send_message(self, message: str) -> None:
        participants = self.chat['participants']
        if not participants[0]['is_human']:
            tgt = participants[0]['user']['username']
        else:
            tgt = participants[1]['user']['username']
        data = self.client.chat.send_message(
            self.chat['external_id'], tgt, message
        )
        text = data['replies'][0]['text']
        return text