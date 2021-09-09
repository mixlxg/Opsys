
function normalcreatetbody(id,mes,per_page_num,format) {
        $("#"+id + " tbody").empty();
        var per_page_num = per_page_num;
        if ($('#'+id+'+ nav').length ==0){
            $('#'+id).parent().append('<nav aria-label="Page navigation" class="text-center"><ul></ul></nav>');
        }
        if (mes.length > per_page_num){
            $('#'+id+'+ nav').children('ul').empty();
            $.each(mes.slice(0,per_page_num),function (i,k) {
                 $("#"+id + " tbody").append(
                    format(k)
                )
            })
            var options = {
            bootstrapMajorVersion:3,
            currentPage: 1,
            totalPages: Math.ceil(mes.length/per_page_num),
            numberOfPages:7,
            size:"normal",
            itemTexts: function (type, page, current) {
                      switch (type) {
                      case "first":
                          return "首页";
                      case "prev":
                          return "上一页";
                      case "next":
                          return "下一页";
                      case "last":
                          return "尾页";
                      case "page":
                          return page;
                      }
                  },
            onPageClicked:function (e,originalEvent,type,page) {
              $("#"+id + " tbody").empty();
              $.each(mes.slice((page-1)*per_page_num,page*per_page_num),function (i,k) {
                $("#"+id + " tbody").append(
                    format(k)
                  )
              })
            }
           }
            $('#'+id+'+ nav').children('ul').bootstrapPaginator(options);
        }else{
            $('#'+id+'+ nav').children('ul').empty();
            $.each(mes,function (i,k) {
                $("#"+id + " tbody").append(
                    format(k)
                )
            })
        }

    }