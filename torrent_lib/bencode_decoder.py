import hashlib
import pprint

class bencode_decoder:

    def is_int(self,char):
        return char>=ord('0') and char<=ord('9')

    def btoi(self,tstr,i=0):
        dint=b""
        i+=1
        while chr(tstr[i])!='e':
            dint+=chr(tstr[i]).encode("utf-8")
            i+=1
        return (int(dint),i)


    def btos(self,tstr,i=0):
        slen=""
        while self.is_int(tstr[i]):
            slen+=chr(tstr[i])
            i+=1
        i+=1
        dstr=""
        j=i+int(slen)
        return (tstr[i:j],j-1)


    def btol(self,tstr,i=0):
        if chr(tstr[i+1])=='e':
            return ([],i+1)
        temp,i=self.decode_helper(tstr,i+1)
        nel=[temp]
        temp2,i=self.btol(tstr,i)
        nel+=temp2
        return (nel,i)


    def btod(self,tstr,i=0):
        if chr(tstr[i+1])=='e':
            return ({},i+1)

        nel1,i=self.decode_helper(tstr,i+1)
        nel2,i=self.decode_helper(tstr,i+1)
        bdict={nel1:nel2}
        temp,i=self.btod(tstr,i)
        bdict.update(temp)
        return (bdict,i)

    def decode_helper(self,tstr,i=0):
        #i (int): The current index (pointer) in the byte string `data` where decoding begins.

        if self.is_int(tstr[i]):
            return self.btos(tstr,i)

        fc=chr(tstr[i])

        if fc=='i':
            return self.btoi(tstr,i)

        if fc=='l':
            return self.btol(tstr,i)

        if fc=='d':
            return self.btod(tstr,i)


    def escape(self,i):
        if (i>=ord('0') and i<=ord('9')) or (i>=ord('a') and i<=ord ('z')) or (i>=ord('A') and i<=ord('Z')) or i==ord('-') or    i==ord('_') or i==ord('.')or i==ord('~'):
            return chr(i)

        if i<=15:
            return hex(i).replace("0x","%0").upper()

        return hex(i).replace("0x","%").upper()

    def escaped_hash(self,hash):
        info_hash=""
        for i in hash:
            info_hash+=self.escape(i)
        return info_hash

    def print_in_format(self,ele,i=0):

        pprint.pprint(ele)
        # if isinstance(ele,dict):
        #     for key in ele:
        #         print(i*" ",key,":")
        #         self.print_in_format(ele[key],i+1)

        # if isinstance(ele,list):
        #     for val in ele:
        #         self.print_in_format(val,i+1)

        # if isinstance(ele,bytes):
        #     print(i*" ",ele)

        # if isinstance(ele,int):
        #     print(i*" ",ele)



    def decode(self,torrent_string):
        return self.decode_helper(torrent_string)[0]

    def decode_file(self,file):
        with open(file,'rb') as f:
            return self.decode(f.read())

    def encode(self,data):

        if type(data)==int:
            return f"i{data}e".encode()

        if type(data)==bytes:
            return f"{len(data)}:".encode()+data

        if type(data)==list:
            return b"l"+b"".join([self.encode(i) for i in data])+b"e"

        if type(data)==dict:
            bdict = b"d"
            for key in data:
                bdict+=self.encode(key)
                bdict+=self.encode(data[key])
            bdict+=b"e"
            return bdict



    def file_size(self,decoded_tf):
        left=0
        if b"files" in decoded_tf[b"info"]:
            sum=0
            for i in decoded_tf[b"info"][b"files"]:
                sum+=i[b"length"]
            left=sum
        else:
            left=int(str(decoded_tf[b"info"]    [b"length"]).encode(),10)
        return left

    def extract_info_hash(self,decoded_tf):
        return hashlib.sha1(self.encode(decoded_tf[b"info"])).digest()


if __name__=='__main__':
    hash=b"\x12\x34\x56\x78\x9a\xbc\xde\xf1\x23\x45\x67\x89\xab\xcd\xef\x12\x34\x56\x78\x9a"
    bd=bencode_decoder()
    escaped_hash=bd.escaped_hash(hash)

    if escaped_hash=="%124Vx%9A%BC%DE%F1%23Eg%89%AB%CD%EF%124Vx%9A":
        print(escaped_hash)
        print("escaped hash is correct")
    else:
        print("escaped hash is incorrect")
